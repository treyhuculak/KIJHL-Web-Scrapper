"""The data the app works with."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, computed_field

# What the feed's official_type_id means. Checked across every league that
# serves summaries — 120 crews, no exceptions — so the role is derived from it
# rather than parsed out of the feed's 'Referee 1' prose and stored twice. An
# unfamiliar slot is shown as a plain official rather than guessed at.
ROLE_BY_SLOT = {1: "Referee", 2: "Referee", 3: "Linesperson", 4: "Linesperson"}


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
    """One of the officials who worked a game. Usually four, but not always."""

    person_id: str
    """The feed's own id for this person, scoped to the league. Every statistic
    keys on it, so nothing rests on two spellings of a name matching."""
    first_name: str
    last_name: str
    """Kept apart from the first name because officials are listed by surname."""
    slot: int
    """The feed's official_type_id — see ROLE_BY_SLOT."""
    number: int | None
    """Their jersey number. Some leagues don't give their officials one."""

    @computed_field
    @property
    def name(self) -> str:
        """The parts are what's stored; this is what a reader sees."""
        return f"{self.first_name} {self.last_name}".strip()

    @computed_field
    @property
    def role(self) -> str:
        return ROLE_BY_SLOT.get(self.slot, "Official")


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


# What gets kept, and what gets read back out.
#
# The games page above works game by game, straight from the feed. These are for
# the seasons of history behind it, which is a different job: what goes into the
# database, and the statistics that come back.


class Season(BaseModel):
    """A season a league has played. Cup tournaments arrive as these too."""

    id: str
    name: str
    playoff: bool
    starts_on: date | None


class Summary(BaseModel):
    """What a game's summary adds to its schedule row.

    Every penalty number is None together when the summary couldn't be read —
    which is a different thing from a game in which nobody took a penalty.
    """

    home_pims: int | None = None
    visitor_pims: int | None = None
    majors: int | None = None
    """Majors and match penalties, fighting aside."""
    fights: int | None = None
    """Fights, counted as exchanges rather than as penalties."""
    officials: list[Official] = Field(default_factory=list)


class GameRecord(BaseModel):
    """A game that has been played, as it goes into storage."""

    id: str
    season_id: str
    played_on: date
    home_code: str
    visitor_code: str
    home_goals: int | None
    visitor_goals: int | None
    last_modified: str
    """The feed's change marker, so a later run can tell what has moved."""
    summary: Summary = Field(default_factory=Summary)


class OfficialSeason(BaseModel):
    """One official's season, counted up out of the games they worked."""

    person_id: str
    name: str
    number: int | None
    role: str
    """The one they worked most often that season; they do swap."""
    games: int
    pims: int
    pims_per_game: float
    majors: int
    """Majors and match penalties called in their games, fighting aside."""
    fights: int
