"""HTTP endpoints."""

from datetime import date

import httpx
from fastapi import APIRouter, HTTPException, Query

from .config import LEAGUES
from .hockeytech import fetch_games
from .models import Game, League

router = APIRouter(prefix="/api")


@router.get("/leagues")
async def list_leagues() -> list[League]:
    """Every league the app can show."""
    return [
        League(id=league.id, name=league.name, accent=league.accent) for league in LEAGUES.values()
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
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502, detail=f"Could not reach the {config.name} feed"
        ) from error
