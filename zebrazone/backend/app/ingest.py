"""Fills the database from the feed.

    python -m app.ingest                     every league, every season since 2022
    python -m app.ingest --recent            only the seasons in play — the nightly job
    python -m app.ingest --league kijhl      one league
    python -m app.ingest --season 65 --league kijhl
    python -m app.ingest --since 2025        from a year of your choosing

Deliberately a command and not an endpoint. A full backfill is some sixteen
thousand requests to someone else's feed; that should be something a person or a
scheduler starts, never something a page view can set off.

Safe to run again at any time. Games are written by their id, and a game whose
feed stamp hasn't moved since we last read it doesn't cost a request — so a
nightly run over a whole season asks for a handful of summaries, not hundreds.
"""

import argparse
import asyncio
from datetime import date, timedelta

from . import hockeytech, store
from .config import BACKFILL_FROM, LEAGUES, RECENT_SEASON_DAYS, LeagueConfig
from .models import GameRecord, Season

# How many games to write at a time. Small enough that a failure loses little,
# large enough that a season isn't thousands of round trips.
BATCH = 200

# Seasons that aren't competition. Pre-season lineups are half prospects and the
# officiating is not the same job, so counting those nights against an official's
# season would flatter or damn them for work nobody was judging.
#
# Matched on the name, because the feed's own flag only separates playoffs from
# everything else — an exhibition and a regular season look identical to it. The
# wording differs by league: 'Pre-Season', 'Pre-season', 'Exhibition',
# 'Exhibition Season'. Cup tournaments are kept: the Mowat and Cyclone Taylor
# cups are championships, played for real and each its own season already.
NOT_COMPETITION = (
    "pre-season",
    "preseason",
    "exhibition",
    "all-star",
    "all star",
    "prospects",
    "test season",
)


async def ingest_league(league: LeagueConfig, earliest: date, only: str | None) -> None:
    """Bring one league up to date."""
    seasons = [s for s in await hockeytech.fetch_seasons(league) if is_competition(s)]
    await store.save_seasons(league.id, seasons)

    wanted = in_scope(seasons, earliest=earliest, only=only)
    if not wanted:
        print(f"{league.id}: nothing to do")
        return

    for season in wanted:
        await _ingest_season(league, season)


def is_competition(season: Season) -> bool:
    """Whether a season is games played for something.

    Regular seasons and playoffs are; pre-seasons, exhibitions and showcase
    games aren't, and don't belong in anybody's record. Playoffs stay marked as
    playoffs — they're their own season here, and read as one.
    """
    name = season.name.lower()
    return not any(word in name for word in NOT_COMPETITION)


def in_scope(seasons: list[Season], *, earliest: date, only: str | None) -> list[Season]:
    """The seasons a run should look at.

    One idea rather than several: the earliest start date worth reading. A
    backfill sets it to the start of a year, the nightly job to fifteen months
    ago, and asking for a single season ignores it altogether.
    """
    if only is not None:
        return [season for season in seasons if season.id == only]
    # A season with no start date can't be placed. Every one we've seen has had
    # one, and leaving it out beats guessing at where it belongs.
    return [
        season
        for season in seasons
        if season.starts_on is not None and season.starts_on >= earliest
    ]


async def _ingest_season(league: LeagueConfig, season: Season) -> None:
    played = await hockeytech.fetch_played_games(league, season.id)
    if not played:
        print(f"{league.id} {season.name}: no games played")
        return

    held = await store.stored_games(league.id, season.id)
    fresh = [game for game in played if held.get(game.id) != game.last_modified]

    print(
        f"{league.id} {season.name}: {len(played)} played, "
        f"{len(fresh)} to read" + (" (all held)" if not fresh else "")
    )
    if not fresh:
        return

    for start in range(0, len(fresh), BATCH):
        batch = fresh[start : start + BATCH]
        summaries = await hockeytech.fetch_summaries(league, [game.id for game in batch])
        for game in batch:
            game.summary = summaries.get(game.id, game.summary)

        await store.save_games(league.id, batch)
        print(f"  {min(start + BATCH, len(fresh))}/{len(fresh)}{_shortfall(batch)}")


def _shortfall(batch: list[GameRecord]) -> str:
    """Say when summaries didn't come back, rather than letting a league quietly
    store nothing but scores. Some keys aren't cleared for that view at all."""
    unread = sum(1 for game in batch if game.summary.home_pims is None)
    return f"  ({unread} without a summary)" if unread else ""


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--league", help="league id; every one by default")
    parser.add_argument("--season", help="a single season id, ignoring the year filters")
    parser.add_argument(
        "--recent",
        action="store_true",
        help="only seasons started in the last 15 months — what a nightly run wants",
    )
    parser.add_argument(
        "--since",
        type=int,
        default=BACKFILL_FROM,
        help=f"earliest season year to read (default {BACKFILL_FROM})",
    )
    args = parser.parse_args()

    if args.league and args.league not in LEAGUES:
        parser.error(f"unknown league: {args.league}. Known: {', '.join(LEAGUES)}")
    leagues = [LEAGUES[args.league]] if args.league else list(LEAGUES.values())

    # Read the clock once, so every league in a run is measured from the same
    # moment and a run that straddles midnight doesn't change its mind halfway.
    today = date.today()
    earliest = today - timedelta(days=RECENT_SEASON_DAYS) if args.recent else date(args.since, 1, 1)
    print(f"reading seasons from {earliest} ({today})")

    await store.open_pool()
    try:
        await store.ensure_schema()
        for league in leagues:
            await ingest_league(league, earliest, args.season)
        print("done")
    finally:
        await store.close_pool()


if __name__ == "__main__":
    asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
