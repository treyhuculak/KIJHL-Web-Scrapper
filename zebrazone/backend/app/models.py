"""The data the app works with."""

from datetime import date

from pydantic import BaseModel


class League(BaseModel):
    """A league, as offered to the client."""

    id: str
    name: str
    accent: str


class Team(BaseModel):
    """One side of a game."""

    code: str
    city: str
    nickname: str
    goals: int
    pims: int
    logo: str


class Penalty(BaseModel):
    """A penalty worth calling out on its own — a major or a misconduct."""

    team_code: str
    player: str
    infraction: str
    minutes: int
    period: str
    time: str


class Game(BaseModel):
    """A single game."""

    id: str
    date: date
    status: str
    final: bool
    venue: str
    start_time: str | None
    attendance: int | None
    home: Team
    visitor: Team
    notable_penalties: list[Penalty]
