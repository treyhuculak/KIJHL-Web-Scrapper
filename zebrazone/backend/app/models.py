"""The data the app works with."""
from datetime import date

from pydantic import BaseModel


class League(BaseModel):
    """A league, as offered to the client."""

    id: str
    name: str


class Team(BaseModel):
    """One side of a game."""

    code: str
    city: str
    nickname: str
    goals: int


class Game(BaseModel):
    """A single game."""

    id: str
    date: date
    status: str
    venue: str
    start_time: str | None
    attendance: int | None
    home: Team
    visitor: Team
