"""Reads games from the HockeyTech feed.

This is the only module that knows what the upstream API looks like.

Three views are involved. `gamesbydate` lists a day's games but says nothing
about penalties, so each game's `gamesummary` is fetched too, and
`teamsbyseason` supplies the logos. All three are the same for every league on
the platform.
"""

import asyncio
from collections import defaultdict
from datetime import date

import httpx

from .config import LeagueConfig
from .models import Game, GameRecord, Official, Penalty, Season, Summary, Team

FEED_URL = "https://lscluster.hockeytech.com/feed/"
TIMEOUT_SECONDS = 15

# A backfill is thousands of requests to someone else's server over twenty-odd
# minutes, and one dropped connection used to end the whole run — the first
# full backfill died on a connect timeout with the WHL read and seven leagues
# to go. Two more tries, a couple of seconds apart.
RETRIES = 2
RETRY_PAUSE_SECONDS = 2

# The statuses that mean 'ask again later' rather than 'stop asking'.
AGAIN_LATER = {429, 500, 502, 503, 504}

# How many summaries to ask for at once when reading a season. The feed is
# someone else's, and a backfill is hundreds of games.
AT_ONCE = 6

# The feed sorts every penalty into one of these classes. Minors are routine;
# these are the ones worth listing out. The BCHL files game misconducts under a
# class of their own where every other league calls them misconducts.
NOTABLE_CLASSES = {"Major", "Match", "Misconduct", "Game Misconduct"}

# The ones counted separately from a game's penalty minutes, because a night of
# majors is not a night of minors.
MAJOR_CLASSES = {"Major", "Match"}

# Fighting is written four ways across these leagues — 'Fighting', 'Major-
# Fighting', 'Fighting - Major (5 Minutes)' — and this is the whole of what they
# have in common.
FIGHTING = "fighting"


class FeedUnavailable(RuntimeError):
    """The feed refused, with HTTP 200 and a plain-text body.

    'Client access denied.' when the key doesn't match the client code, 'Feed
    type access denied.' when the key isn't cleared for that view.
    """


async def fetch_games(league: LeagueConfig, day: date) -> list[Game]:
    """Return every game the league played on `day`."""
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        listing = await _get(
            client, league, feed="modulekit", view="gamesbydate", fetch_date=day.isoformat()
        )
        entries = listing.get("SiteKit", {}).get("Gamesbydate", [])
        if not entries:
            return []

        # None of these depend on each other, so ask for them all at once: the
        # season's logos, then one summary per game.
        logos, *summaries = await asyncio.gather(
            _fetch_logos(client, league, entries[0]["season_id"]),
            *(_fetch_summary(client, league, entry["id"]) for entry in entries),
        )

    # strict: there is exactly one summary per entry, and a mismatch would
    # silently pair the wrong penalties with the wrong game.
    return [
        _read_game(entry, summary, logos) for entry, summary in zip(entries, summaries, strict=True)
    ]


async def fetch_seasons(league: LeagueConfig) -> list[Season]:
    """Every season the league has on the platform, newest first.

    Playoffs, pre-seasons and exhibitions are all seasons in their own right
    here, as are one-off cup and all-star games of half a dozen fixtures.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        payload = await _get(client, league, feed="modulekit", view="seasons")

    seasons = [
        Season(
            id=str(row["season_id"]),
            name=row.get("season_name", ""),
            playoff=str(row.get("playoff")) == "1",
            starts_on=row.get("start_date") or None,
        )
        for row in payload.get("SiteKit", {}).get("Seasons") or []
    ]
    return sorted(seasons, key=lambda season: season.starts_on or date.min, reverse=True)


async def fetch_played_games(league: LeagueConfig, season_id: str) -> list[GameRecord]:
    """Every game of a season that has been played, from the schedule alone.

    One request for the lot. What it can't say — the penalty minutes, and who
    worked the game — is a summary each, which is the expensive half and is left
    for the caller to ask for.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        payload = await _get(
            client, league, feed="modulekit", view="schedule", season_id=season_id, team_id="all"
        )

    return [
        _read_scheduled(row, season_id)
        for row in payload.get("SiteKit", {}).get("Schedule") or []
        if str(row.get("game_status", "")).startswith("Final")
    ]


async def fetch_summaries(league: LeagueConfig, game_ids: list[str]) -> dict[str, Summary]:
    """What the summaries add for a set of games, a few at a time.

    A game whose summary won't load comes back as an empty Summary rather than
    not at all: some leagues aren't cleared to read the view, and their games are
    still games.
    """
    at_once = asyncio.Semaphore(AT_ONCE)

    async def one(client: httpx.AsyncClient, game_id: str) -> tuple[str, Summary]:
        async with at_once:
            return game_id, _read_summary(await _fetch_summary(client, league, game_id))

    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        return dict(await asyncio.gather(*(one(client, game_id) for game_id in game_ids)))


def _transient(error: Exception) -> bool:
    """Whether asking again could plausibly get a different answer.

    A dropped connection or a server having a moment, yes. A refusal, a 404 or
    a 403, no — those say the same thing however many times you ask, and the
    callers that tolerate them are waiting to hear it rather than to wait.
    """
    if isinstance(error, httpx.TransportError):
        return True
    return isinstance(error, httpx.HTTPStatusError) and error.response.status_code in AGAIN_LATER


async def _get(client: httpx.AsyncClient, league: LeagueConfig, **params: str) -> dict:
    """One call to the feed, asked again if the failure was worth re-asking.

    Only the transport-level failures are retried. The feed refusing a view it
    hasn't cleared the key for is not a failure to retry — it's an answer, and
    `_fetch_summary` and `_fetch_logos` are written to accept it.
    """
    for attempt in range(RETRIES):
        try:
            return await _once(client, league, **params)
        except (httpx.HTTPError, FeedUnavailable) as error:
            if not _transient(error):
                raise
            await asyncio.sleep(RETRY_PAUSE_SECONDS * (attempt + 1))

    # Whatever the last try does is the caller's to hear about.
    return await _once(client, league, **params)


async def _once(client: httpx.AsyncClient, league: LeagueConfig, **params: str) -> dict:
    """One call to the feed, with the credentials every call needs."""
    response = await client.get(
        FEED_URL,
        params={
            "key": league.api_key,
            "client_code": league.client_code,
            "lang_code": "en",
            "fmt": "json",
            **params,
        },
    )
    response.raise_for_status()
    try:
        return response.json()
    except ValueError as error:
        raise FeedUnavailable(response.text.strip()[:80]) from error


async def _fetch_summary(client: httpx.AsyncClient, league: LeagueConfig, game_id: str) -> dict:
    """A game's detail view: penalty minutes per team, and every penalty called.

    A game whose summary won't load still belongs on the page, just without its
    penalty numbers — some leagues aren't cleared to read this view at all.
    """
    try:
        payload = await _get(client, league, feed="gc", tab="gamesummary", game_id=game_id)
    except (httpx.HTTPError, FeedUnavailable):
        return {}
    return payload.get("GC", {}).get("Gamesummary") or {}


async def _fetch_logos(
    client: httpx.AsyncClient, league: LeagueConfig, season_id: str
) -> dict[str, str]:
    """Team id to logo URL, for the whole season.

    The image's file extension varies from team to team, so the feed's own list
    is the only reliable way to build these URLs. Logos are a nicety; a league
    whose list won't load falls back to team codes.
    """
    try:
        payload = await _get(
            client, league, feed="modulekit", view="teamsbyseason", season_id=season_id
        )
    except (httpx.HTTPError, FeedUnavailable):
        return {}
    teams = payload.get("SiteKit", {}).get("Teamsbyseason") or []
    return {team["id"]: team.get("team_logo_url", "") for team in teams}


def _read_game(entry: dict, summary: dict, logos: dict[str, str]) -> Game:
    """Turn one feed entry, plus its summary, into a Game."""
    # A finished game's status is 'Final', 'Final OT' or 'Final SO'; one still to
    # come carries its start time instead, e.g. '6:05 pm PDT'.
    status = entry.get("game_status", "Unknown")

    pims = summary.get("pimTotal") or {}
    home = _read_team(entry, "home", pims.get("home"), logos)
    visitor = _read_team(entry, "visiting", pims.get("visitor"), logos)

    return Game(
        id=entry["id"],
        date=entry["date_played"],
        status=status,
        final=status.startswith("Final"),
        venue=entry.get("venue", ""),
        start_time=entry.get("schedule_time") or None,
        attendance=_number(entry.get("attendance")),
        home=home,
        visitor=visitor,
        notable_penalties=[
            _read_penalty(penalty, home.code, visitor.code)
            for penalty in summary.get("penalties") or []
            if penalty.get("penalty_class") in NOTABLE_CLASSES
        ],
        officials=_read_officials(summary),
    )


def _read_scheduled(row: dict, season_id: str) -> GameRecord:
    """One row of a season's schedule, before its summary has been read."""
    return GameRecord(
        id=str(row["id"]),
        season_id=season_id,
        played_on=row["date_played"],
        home_code=row.get("home_team_code", ""),
        visitor_code=row.get("visiting_team_code", ""),
        home_goals=_number(row.get("home_goal_count")),
        visitor_goals=_number(row.get("visiting_goal_count")),
        last_modified=str(row.get("last_modified") or ""),
    )


def _read_summary(summary: dict) -> Summary:
    """What a game's summary adds. An empty one means it couldn't be read."""
    if not summary:
        return Summary()

    pims = summary.get("pimTotal") or {}
    majors, fights = _count_majors(summary.get("penalties") or [])
    return Summary(
        home_pims=_number(pims.get("home")),
        visitor_pims=_number(pims.get("visitor")),
        majors=majors,
        fights=fights,
        officials=_read_officials(summary),
    )


def _count_majors(penalties: list[dict]) -> tuple[int, int]:
    """The game's majors and match penalties, and the fights among them.

    A fight is an exchange rather than a penalty. Two players from opposite
    sides fighting at one stoppage is one fight, four fighting majors at the
    same stoppage is two, and a fighting major with nobody opposite it — a
    player jumped, an aggressor — is no fight at all and counts as the major it
    is. Pairing them off across the two sides gets all three right.

    A stoppage is the period and the clock, which the feed gives in seconds.
    """
    majors = 0
    fighting: dict[tuple[str, str], list[bool]] = defaultdict(list)

    for penalty in penalties:
        if penalty.get("penalty_class") not in MAJOR_CLASSES:
            continue
        if FIGHTING in (penalty.get("lang_penalty_description") or "").lower():
            stoppage = (str(penalty.get("period_id")), str(penalty.get("s")))
            fighting[stoppage].append(penalty.get("home") == "1")
        else:
            majors += 1

    fights = 0
    for sides in fighting.values():
        home = sum(sides)
        away = len(sides) - home
        fights += min(home, away)
        # Whoever was left without an opponent was not in a fight.
        majors += abs(home - away)

    return majors, fights


def _read_officials(summary: dict) -> list[Official]:
    """The on-ice crew, in the order the feed lists them.

    Usually four. Occasionally three, and once in a while none at all, so
    nothing downstream may assume a crew size.
    """
    crew = []
    for entry in summary.get("officialsOnIce") or []:
        person_id = str(entry.get("person_id") or "").strip()
        first = (entry.get("first_name") or "").strip()
        last = (entry.get("last_name") or "").strip()
        # Without an id there is nothing to count them under, and a nameless
        # official is nobody. Either way the row would be noise.
        if not person_id or not (first or last):
            continue
        crew.append(
            Official(
                person_id=person_id,
                first_name=first,
                last_name=last,
                slot=_number(entry.get("official_type_id")) or 0,
                # Leagues that don't number their officials send a zero.
                number=_number(entry.get("jersey_number")) or None,
            )
        )
    return crew


def _read_team(entry: dict, side: str, pims: object, logos: dict[str, str]) -> Team:
    """One side of a game. The feed names these fields 'home' or 'visiting'."""
    return Team(
        code=entry.get(f"{side}_team_code", ""),
        city=entry.get(f"{side}_team_city", ""),
        nickname=entry.get(f"{side}_team_nickname", ""),
        goals=_number(entry.get(f"{side}_goal_count")) or 0,
        # None, not 0: a summary we couldn't read is not a penalty-free game.
        pims=_number(pims),
        logo=logos.get(entry.get(f"{side}_team", ""), ""),
    )


def _read_penalty(entry: dict, home_code: str, visitor_code: str) -> Penalty:
    """Turn one penalty from a game summary into a Penalty."""
    # Bench penalties name whoever served them, and sometimes nobody at all.
    player = entry.get("player_penalized_info") or entry.get("player_served_info") or {}
    name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()

    return Penalty(
        # The home flag beats the player's team: it's there for bench penalties too.
        team_code=home_code if entry.get("home") == "1" else visitor_code,
        player=name or "Bench",
        infraction=(entry.get("lang_penalty_description") or "").strip(),
        minutes=_number(entry.get("minutes")) or 0,
        period=entry.get("period", ""),
        time=entry.get("time_off_formatted", ""),
    )


def _number(value: object) -> int | None:
    """The feed sends numbers as ints or as strings, and blanks when missing."""
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
