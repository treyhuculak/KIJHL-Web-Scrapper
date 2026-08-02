"""Reads games from the HockeyTech feed.

This is the only module that knows what the upstream API looks like.

Three views are involved. `gamesbydate` lists a day's games but says nothing
about penalties, so each game's `gamesummary` is fetched too, and
`teamsbyseason` supplies the logos. All three are the same for every league on
the platform.
"""

import asyncio
import re
from datetime import date

import httpx

from .config import LeagueConfig
from .models import Game, Official, Penalty, Team

FEED_URL = "https://lscluster.hockeytech.com/feed/"
TIMEOUT_SECONDS = 15

# The feed sorts every penalty into one of these classes. Minors are routine;
# these are the ones worth listing out.
NOTABLE_CLASSES = {"Major", "Misconduct"}

# An official is described by role and slot, e.g. 'Referee 1'. The slot says
# nothing a reader needs, so it comes off.
OFFICIAL_SLOT = re.compile(r"\s*\d+$")

# The feed still says 'Linesman'. We say linesperson, everywhere.
ROLE_NAMES = {"Linesman": "Linesperson"}


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


async def _get(client: httpx.AsyncClient, league: LeagueConfig, **params: str) -> dict:
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
    return response.json()


async def _fetch_summary(client: httpx.AsyncClient, league: LeagueConfig, game_id: str) -> dict:
    """A game's detail view: penalty minutes per team, and every penalty called.

    A game whose summary won't load still belongs on the page, just without its
    penalty numbers.
    """
    try:
        payload = await _get(client, league, feed="gc", tab="gamesummary", game_id=game_id)
    except httpx.HTTPError:
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
    except httpx.HTTPError:
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


def _read_officials(summary: dict) -> list[Official]:
    """The on-ice crew, in the order the feed lists them."""
    crew = []
    for entry in summary.get("officialsOnIce") or []:
        name = f"{entry.get('first_name', '')} {entry.get('last_name', '')}".strip()
        if not name:
            continue
        role = OFFICIAL_SLOT.sub("", entry.get("description") or "").strip()
        crew.append(
            Official(
                name=name,
                role=ROLE_NAMES.get(role, role) or "Official",
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
        pims=_number(pims) or 0,
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
