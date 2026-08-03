"""HTTP endpoints."""

from datetime import date

import httpx
from fastapi import APIRouter, HTTPException, Query

from .config import LEAGUES
from .hockeytech import FeedUnavailable, fetch_games
from .models import Game, League, Tier

router = APIRouter(prefix="/api")


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
    config = LEAGUES.get(league.lower())
    if config is None:
        raise HTTPException(status_code=404, detail=f"Unknown league: {league}")

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
