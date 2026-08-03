"""The data the app works with."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class Tier(StrEnum):
    """The level a league plays at.

    The picker groups leagues under these headings, in the order declared here —
    so this is also the order the tiers appear on screen.
    """

    MAJOR = "Major junior"
    JUNIOR_A = "Junior A"
    JUNIOR_B = "Junior B"


class League(BaseModel):
    """A league, as offered to the client."""

    id: str
    name: str
    accent: str
    tier: Tier


class Team(BaseModel):
    """One side of a game."""

    code: str
    city: str
    nickname: str
    goals: int
    pims: int | None
    logo: str


class Penalty(BaseModel):
    """A penalty worth calling out on its own — a major or a misconduct."""

    team_code: str
    player: str
    infraction: str
    minutes: int
    period: str
    time: str


class Official(BaseModel):
    """One of the four officials who worked the game."""

    name: str
    role: str
    """'Referee' or 'Linesperson', without the slot number the feed appends."""
    number: int | None
    """Their jersey number. Some leagues don't give their officials one."""


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
    officials: list[Official]
