"""Reads and writes the seasons of history.

This is the only module that knows SQL, in the same way `hockeytech.py` is the
only one that knows the feed. Everything above the two of them works in `Game`,
`Season` and `OfficialSeason`, so a change of database reaches one file.

The connection string comes from DATABASE_URL. Without one the app still runs —
the games page reads the feed directly and needs nothing stored — and anything
that wants history says so plainly instead of failing oddly.
"""

import asyncio
from pathlib import Path

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from .config import DATABASE_URL, SUMMARY_RETRY_DAYS
from .models import (
    CrewedGame,
    GameRecord,
    Official,
    OfficialSeason,
    Partnership,
    Season,
    SeasonStats,
    leaderboard,
    role_for,
    slots_for,
)

SCHEMA = Path(__file__).with_name("schema.sql")

# How many rows a leaderboard holds. Short enough to read at a glance and to be
# worth reading: past the first few, one more game worked is the whole story.
TOP = 5

_pool: AsyncConnectionPool | None = None


class NotConfigured(RuntimeError):
    """Asked for history when no database has been set up."""


def _check_loop() -> None:
    """Fail now, and say why, rather than in thirty seconds and not.

    psycopg's async driver needs an event loop that can watch a socket, which
    Windows' proactor loop cannot. Uvicorn hands out the selector loop whenever
    it runs the server in a subprocess — which `--reload` does, and which
    `npm run locally` therefore does — but plain `uvicorn app.main:app` on
    Windows gets the proactor one and every connection quietly times out.
    Nothing here applies on Linux, where the selector loop is the only one.
    """
    proactor = getattr(asyncio, "ProactorEventLoop", None)
    if proactor is not None and isinstance(asyncio.get_running_loop(), proactor):
        raise RuntimeError(
            "psycopg cannot use Windows' proactor event loop. Run the server with "
            "--reload (as `npm run locally` does), which puts uvicorn on the "
            "selector loop."
        )


async def _prepare(connection: AsyncConnection) -> None:
    """Settle a new connection before it's handed out.

    Neon's pooled endpoint pools by transaction, so the server-side statement a
    prepared query leaves behind may not be there for the next one. Turning
    preparation off is what makes the pooled endpoint usable at all.
    """
    connection.prepare_threshold = None


# How long an unused connection is kept. Comfortably inside Neon's idle window,
# so the pool lets go of a connection before the database does.
IDLE_SECONDS = 120


async def open_pool() -> None:
    """Build the pool. Nothing here connects to anything.

    The first query opens the first connection, and on Neon's free tier that is
    the whole point: the compute suspends when idle and is billed for the time
    it spends awake, so connecting at startup would charge a database wake to
    every cold start — including the ones that only ever serve the games page,
    which reads the feed live and never asks the database anything.

    The laziness is `min_size=0`, not the absence of a query. A pool with a
    minimum keeps that many connections up from the moment it opens, which
    wakes the database just as surely as asking it something would.

    The cost is real and lands on one reader: whoever first opens a stats or
    officials page after a quiet spell waits for the wake, which is the better
    part of a second. That used to be paid at boot, overlapping the browser
    fetching its JavaScript. It is a worse deal for one person and a much
    better one for the compute budget, which is what runs out.
    """
    global _pool
    if not DATABASE_URL:
        return

    _check_loop()
    _pool = AsyncConnectionPool(
        DATABASE_URL,
        min_size=0,
        max_size=4,
        # Nothing held across a suspend, or we would hand out a dead connection.
        max_idle=IDLE_SECONDS,
        # And if one dies behind our back anyway — a suspend we mistimed, a
        # compute moving — that costs a reconnection rather than somebody's page.
        check=AsyncConnectionPool.check_connection,
        configure=_prepare,
        kwargs={"row_factory": dict_row},
        open=False,
    )
    await _pool.open(wait=False)


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def _ready() -> AsyncConnectionPool:
    if _pool is None:
        raise NotConfigured("No DATABASE_URL is set, so there is no history to read.")
    return _pool


async def ensure_schema() -> None:
    """Create anything missing. Every statement in schema.sql is IF NOT EXISTS,
    so this is safe to run before each ingest and cheap when there's nothing
    to do."""
    async with _ready().connection() as connection:
        await connection.execute(SCHEMA.read_text(encoding="utf-8"))


# Writing


async def save_seasons(league_id: str, seasons: list[Season]) -> None:
    if not seasons:
        return

    async with _ready().connection() as connection, connection.cursor() as cursor:
        await cursor.executemany(
            """
            INSERT INTO season (league_id, season_id, name, playoff, starts_on)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (league_id, season_id) DO UPDATE
               SET name = EXCLUDED.name,
                   playoff = EXCLUDED.playoff,
                   starts_on = EXCLUDED.starts_on
            """,
            [(league_id, s.id, s.name, s.playoff, s.starts_on) for s in seasons],
        )


async def save_games(league_id: str, games: list[GameRecord]) -> None:
    """Write a batch of games, their officials, and who worked what.

    All of it in one transaction: a run that dies halfway leaves the season as
    it was rather than half-rewritten.
    """
    if not games:
        return

    async with _ready().connection() as connection:
        async with connection.transaction(), connection.cursor() as cursor:
            await cursor.executemany(
                """
                INSERT INTO game (league_id, game_id, season_id, played_on,
                                  home_code, visitor_code, home_goals, visitor_goals,
                                  home_pims, visitor_pims, majors, fights, last_modified)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (league_id, game_id) DO UPDATE
                   SET season_id = EXCLUDED.season_id,
                       played_on = EXCLUDED.played_on,
                       home_code = EXCLUDED.home_code,
                       visitor_code = EXCLUDED.visitor_code,
                       home_goals = EXCLUDED.home_goals,
                       visitor_goals = EXCLUDED.visitor_goals,
                       -- Only when we have something. A run that skipped this
                       -- game's summary must not wipe the last one's work.
                       home_pims = coalesce(EXCLUDED.home_pims, game.home_pims),
                       visitor_pims = coalesce(EXCLUDED.visitor_pims, game.visitor_pims),
                       majors = coalesce(EXCLUDED.majors, game.majors),
                       fights = coalesce(EXCLUDED.fights, game.fights),
                       last_modified = EXCLUDED.last_modified
                """,
                [
                    (
                        league_id,
                        game.id,
                        game.season_id,
                        game.played_on,
                        game.home_code,
                        game.visitor_code,
                        game.home_goals,
                        game.visitor_goals,
                        game.summary.home_pims,
                        game.summary.visitor_pims,
                        game.summary.majors,
                        game.summary.fights,
                        game.last_modified,
                    )
                    for game in games
                ],
            )

            crewed = [game for game in games if game.summary.officials]
            if not crewed:
                return

            await cursor.executemany(
                """
                INSERT INTO official (league_id, person_id, first_name, last_name, number)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (league_id, person_id) DO UPDATE
                   SET first_name = EXCLUDED.first_name,
                       last_name = EXCLUDED.last_name,
                       number = coalesce(EXCLUDED.number, official.number)
                """,
                [
                    (league_id, o.person_id, o.first_name, o.last_name, o.number)
                    for game in crewed
                    for o in game.summary.officials
                ],
            )

            # Replaced rather than merged: a crew that has been corrected should
            # not leave the official it replaced still credited with the game.
            await cursor.execute(
                "DELETE FROM game_official WHERE league_id = %s AND game_id = ANY(%s)",
                (league_id, [game.id for game in crewed]),
            )
            await cursor.executemany(
                """
                INSERT INTO game_official (league_id, game_id, person_id, slot)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                [
                    (league_id, game.id, o.person_id, o.slot)
                    for game in crewed
                    for o in game.summary.officials
                ],
            )


# Reading


async def stored_games(league_id: str, season_id: str) -> dict[str, str]:
    """Which of a season's games we already hold, and how the feed last stamped
    them. An unchanged stamp is what lets a nightly run skip a summary."""
    async with _ready().connection() as connection:
        rows = await connection.execute(
            """
            SELECT game_id,
                   -- A game whose summary never loaded is reported unstamped, so
                   -- the next run asks again rather than trusting a row with no
                   -- numbers in it. Summaries do sometimes arrive a day or two
                   -- late, so that's worth doing — but only for a fortnight.
                   -- After that one isn't coming, and asking every night for the
                   -- rest of time is a request nobody is owed.
                   CASE
                       WHEN home_pims IS NULL AND played_on >= current_date - %s::int THEN ''
                       ELSE last_modified
                   END AS stamp
              FROM game
             WHERE league_id = %s AND season_id = %s
            """,
            (SUMMARY_RETRY_DAYS, league_id, season_id),
        )
        return {row["game_id"]: row["stamp"] for row in await rows.fetchall()}


async def seasons(league_id: str) -> list[Season]:
    """The seasons we hold games for, the one being played first.

    Ordered by their most recent game rather than by when they started, which
    is what makes the first row the season in play: a league's playoffs start
    later than its regular season but only overtake it once they're under way,
    and the join to the games is also what keeps a season nobody has played yet
    out of the list.
    """
    async with _ready().connection() as connection:
        rows = await connection.execute(
            """
            SELECT s.season_id, s.name, s.playoff, s.starts_on
              FROM season s
              JOIN (SELECT league_id, season_id, max(played_on) AS latest
                      FROM game
                     GROUP BY league_id, season_id) g
             USING (league_id, season_id)
             WHERE s.league_id = %s
             ORDER BY g.latest DESC
            """,
            (league_id,),
        )
        return [
            Season(
                id=row["season_id"],
                name=row["name"],
                playoff=row["playoff"],
                starts_on=row["starts_on"],
            )
            for row in await rows.fetchall()
        ]


async def officials_in_season(league_id: str, season_id: str) -> list[OfficialSeason]:
    """Every official who worked that season, busiest first.

    Games without penalty minutes are left out of the count rather than counted
    as clean ones — a summary that wouldn't load isn't a quiet night.
    """
    async with _ready().connection() as connection:
        rows = await connection.execute(
            """
            SELECT o.person_id,
                   o.first_name,
                   o.last_name,
                   o.number,
                   -- One slot per game worked, which role_for weighs up into
                   -- the job or jobs they did. Kept as a list rather than
                   -- tallied here so that what a slot means stays in one place,
                   -- beside ROLE_BY_SLOT, instead of being half in SQL.
                   array_agg(go.slot)                   AS slots,
                   count(*)                             AS games,
                   sum(g.home_pims + g.visitor_pims)    AS pims,
                   sum(g.majors)                        AS majors,
                   sum(g.fights)                        AS fights
              FROM game_official go
              JOIN game g     USING (league_id, game_id)
              JOIN official o USING (league_id, person_id)
             WHERE g.league_id = %s
               AND g.season_id = %s
               AND g.home_pims IS NOT NULL
             GROUP BY o.person_id, o.first_name, o.last_name, o.number
             ORDER BY games DESC, o.last_name
            """,
            (league_id, season_id),
        )
        return [
            OfficialSeason(
                person_id=row["person_id"],
                name=f"{row['first_name']} {row['last_name']}".strip(),
                number=row["number"],
                role=role_for(row["slots"]),
                games=row["games"],
                pims=row["pims"] or 0,
                pims_per_game=round((row["pims"] or 0) / row["games"], 1),
                majors=row["majors"] or 0,
                fights=row["fights"] or 0,
            )
            for row in await rows.fetchall()
        ]


# A season's standouts.
#
# Three questions, and none of them is the one the officials table answers.
# That table is every official and every figure; these are the few rows at the
# top of one figure at a time, plus the games and the pairings behind them.


WILDEST = """
    SELECT game_id, played_on, home_code, visitor_code, home_goals, visitor_goals,
           home_pims + visitor_pims AS pims, majors, fights
      FROM game
     WHERE league_id = %s AND season_id = %s AND home_pims IS NOT NULL
     ORDER BY pims DESC, played_on
     LIMIT %s
"""

CREWS = """
    SELECT go.game_id, o.person_id, o.first_name, o.last_name, o.number, go.slot
      FROM game_official go
      JOIN official o USING (league_id, person_id)
     WHERE go.league_id = %s AND go.game_id = ANY(%s)
     ORDER BY go.slot
"""

# Who works with whom, counted a night at a time.
#
# The pair, not the crew: an exact foursome almost never repeats — 462 KIJHL
# games last season produced 435 distinct crews, and the most any one of them
# worked together was three — while two referees are put together eight or nine
# times. A crew leaderboard would be a list of one-offs; this isn't.
PARTNERSHIPS = """
    WITH nights AS (
        SELECT array_agg(o.person_id ORDER BY o.last_name, o.first_name, o.person_id) AS pair,
               array_agg(o.first_name || ' ' || o.last_name
                         ORDER BY o.last_name, o.first_name, o.person_id) AS names,
               g.home_pims + g.visitor_pims AS pims
          FROM game g
          JOIN game_official go USING (league_id, game_id)
          JOIN official o       USING (league_id, person_id)
         WHERE g.league_id = %s
           AND g.season_id = %s
           AND g.home_pims IS NOT NULL
           AND go.slot = ANY(%s)
         GROUP BY g.game_id, g.home_pims, g.visitor_pims
        -- Both of them, or it isn't a pairing: a three-man crew leaves one
        -- referee or one linesperson working the job alone.
        HAVING count(*) = 2
    )
    SELECT names, count(*) AS games, avg(pims) AS pims_per_game
      FROM nights
     GROUP BY pair, names
     ORDER BY games DESC, pims_per_game DESC
     LIMIT %s
"""


async def _wildest_games(
    connection: AsyncConnection, league_id: str, season_id: str
) -> list[CrewedGame]:
    """The season's heaviest nights, and who worked them.

    Two queries rather than one: the games are found by their own numbers, then
    the crews are fetched for the handful that won. Aggregating four officials
    into each row of the first query would mean grouping every game in the
    season to keep five.
    """
    rows = await (await connection.execute(WILDEST, (league_id, season_id, TOP))).fetchall()
    if not rows:
        return []

    crews: dict[str, list[Official]] = {}
    crewed = await connection.execute(CREWS, (league_id, [row["game_id"] for row in rows]))
    for member in await crewed.fetchall():
        crews.setdefault(member["game_id"], []).append(
            Official(
                person_id=member["person_id"],
                first_name=member["first_name"],
                last_name=member["last_name"],
                slot=member["slot"],
                number=member["number"],
            )
        )

    return [
        CrewedGame(
            game_id=row["game_id"],
            played_on=row["played_on"],
            home_code=row["home_code"],
            visitor_code=row["visitor_code"],
            home_goals=row["home_goals"],
            visitor_goals=row["visitor_goals"],
            pims=row["pims"],
            majors=row["majors"] or 0,
            fights=row["fights"] or 0,
            crew=crews.get(row["game_id"], []),
        )
        for row in rows
    ]


async def _partnerships(
    connection: AsyncConnection, league_id: str, season_id: str, role: str
) -> list[Partnership]:
    """The pairs of one job put together most often."""
    rows = await connection.execute(PARTNERSHIPS, (league_id, season_id, slots_for(role), TOP))
    return [
        Partnership(
            names=row["names"],
            games=row["games"],
            pims_per_game=round(float(row["pims_per_game"]), 1),
        )
        for row in await rows.fetchall()
    ]


async def season_stats(league_id: str, season_id: str) -> SeasonStats:
    """What stood out about a season.

    The two people boards are read off the same season the officials table is,
    so a name can't say one thing on one page and another on the next.
    """
    officials = await officials_in_season(league_id, season_id)

    async with _ready().connection() as connection:
        return SeasonStats(
            fights=leaderboard(officials, lambda one: one.fights, "Linesperson", TOP),
            majors=leaderboard(officials, lambda one: one.majors, "Referee", TOP),
            wildest=await _wildest_games(connection, league_id, season_id),
            referee_pairs=await _partnerships(connection, league_id, season_id, "Referee"),
            line_pairs=await _partnerships(connection, league_id, season_id, "Linesperson"),
        )
