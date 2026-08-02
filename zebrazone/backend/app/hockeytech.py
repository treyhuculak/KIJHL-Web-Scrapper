"""Reads games from the HockeyTech feed.

This is the only module that knows what the upstream API looks like.
"""
from datetime import date

import httpx

from .config import LeagueConfig
from .models import Game, Team

FEED_URL = "https://lscluster.hockeytech.com/feed/"
TIMEOUT_SECONDS = 15


async def fetch_games(league: LeagueConfig, day: date) -> list[Game]:
    """Return every game the league played on `day`."""
    params = {
        "feed": "modulekit",
        "view": "gamesbydate",
        "fetch_date": day.isoformat(),
        "key": league.api_key,
        "client_code": league.client_code,
        "lang_code": "en",
        "fmt": "json",
    }

    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        response = await client.get(FEED_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    entries = payload.get("SiteKit", {}).get("Gamesbydate", [])
    return [_read_game(entry) for entry in entries]


def _read_game(entry: dict) -> Game:
    """Turn one feed entry into a Game."""
    return Game(
        id=entry["id"],
        date=entry["date_played"],
        status=entry.get("game_status", "Unknown"),
        venue=entry.get("venue", ""),
        start_time=entry.get("schedule_time") or None,
        attendance=_number(entry.get("attendance")),
        home=Team(
            code=entry.get("home_team_code", ""),
            city=entry.get("home_team_city", ""),
            nickname=entry.get("home_team_nickname", ""),
            goals=_number(entry.get("home_goal_count")) or 0,
        ),
        visitor=Team(
            code=entry.get("visiting_team_code", ""),
            city=entry.get("visiting_team_city", ""),
            nickname=entry.get("visiting_team_nickname", ""),
            goals=_number(entry.get("visiting_goal_count")) or 0,
        ),
    )


def _number(value: str | None) -> int | None:
    """The feed sends numbers as strings, and blanks for missing values."""
    if not value:
        return None
    return int(value) if value.isdigit() else None
