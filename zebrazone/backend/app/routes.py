"""HTTP endpoints."""

from datetime import date

import httpx
from fastapi import APIRouter, HTTPException, Query

from . import store
from .config import LEAGUES, LeagueConfig
from .hockeytech import FeedUnavailable, fetch_games
from .models import Game, League, OfficialSeason, Season, Tier

router = APIRouter(prefix="/api")


def _known(league: str) -> LeagueConfig:
    """The league asked for, or a 404 naming it.

    Hidden leagues answer here as well: taking one out of the picker is about
    what's finished enough to announce, not about locking anybody out.
    """
    config = LEAGUES.get(league.lower())
    if config is None:
        raise HTTPException(status_code=404, detail=f"Unknown league: {league}")
    return config


@router.get("/leagues")
async def list_leagues() -> list[League]:
    """Every league on offer to the public, major junior first.

    Sorted by tier so the picker can group them from the order it's handed, and
    config.py never has to be kept in any particular order.
    """
    order = list(Tier)
    on_offer = sorted(
        (league for league in LEAGUES.values() if league.visible),
        key=lambda league: order.index(league.tier),
    )
    return [
        League(id=league.id, name=league.name, accent=league.accent, tier=league.tier)
        for league in on_offer
    ]


@router.get("/games")
async def list_games(
    league: str = Query(..., description="League id, e.g. 'whl'"),
    day: date = Query(..., alias="date", description="Day to look up, YYYY-MM-DD"),
) -> list[Game]:
    """Every game a league played on a given day."""
    config = _known(league)

    try:
        return await fetch_games(config, day)
    except FeedUnavailable as error:
        raise HTTPException(
            status_code=502, detail=f"The {config.name} feed refused the request: {error}"
        ) from error
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502, detail=f"Could not reach the {config.name} feed"
        ) from error


# Stored history. Both of these read the database rather than the feed, so both
# can be asked for before there is one — which is a 503 rather than an error,
# because nothing is wrong with the request and the answer may exist tomorrow.


@router.get("/seasons")
async def list_seasons(
    league: str = Query(..., description="League id, e.g. 'whl'"),
) -> list[Season]:
    """The seasons we hold games for, the one being played first."""
    config = _known(league)
    try:
        return await store.seasons(config.id)
    except store.NotConfigured as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/officials")
async def list_officials(
    league: str = Query(..., description="League id, e.g. 'whl'"),
    season: str = Query(..., description="Season id, from /api/seasons"),
) -> list[OfficialSeason]:
    """Every official who worked a season, busiest first.

    One season at a time, on purpose. Playoffs arrive as their own season here,
    as they do upstream, so nothing is ever silently averaged across two.
    """
    config = _known(league)
    try:
        return await store.officials_in_season(config.id, season)
    except store.NotConfigured as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
