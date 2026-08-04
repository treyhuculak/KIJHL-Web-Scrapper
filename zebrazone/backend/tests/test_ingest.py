"""Which seasons a run decides to look at.

The nightly job's whole economy rests on this: read the seasons in play, leave
the finished ones alone. Getting it wrong is either a hundred pointless requests
a night or a season silently never updating.
"""

from datetime import date, timedelta

import pytest

from app.config import RECENT_SEASON_DAYS
from app.ingest import in_scope, is_competition
from app.models import Season


def season(id: str, starts_on: str | None, name: str = "Regular Season") -> Season:
    return Season(
        id=id,
        name=name,
        playoff=False,
        starts_on=date.fromisoformat(starts_on) if starts_on else None,
    )


SEASONS = [
    season("70", "2026-09-01", "2026/27 Regular Season"),
    season("69", "2026-03-01", "2025-26 Playoffs"),
    season("65", "2025-09-19", "2025/26 Regular Season"),
    season("60", "2023-09-15", "2023/24 Regular Season"),
    season("50", "2019-09-20", "2019/20 Regular Season"),
]


def ids(seasons: list[Season]) -> list[str]:
    return [s.id for s in seasons]


def test_a_named_season_ignores_the_date_entirely():
    """Asking for one season by id should get it however old it is."""
    assert ids(in_scope(SEASONS, earliest=date(2026, 1, 1), only="50")) == ["50"]


def test_a_named_season_that_does_not_exist_finds_nothing():
    assert in_scope(SEASONS, earliest=date(2000, 1, 1), only="nope") == []


def test_a_backfill_takes_everything_from_its_year():
    assert ids(in_scope(SEASONS, earliest=date(2022, 1, 1), only=None)) == ["70", "69", "65", "60"]


def test_a_nightly_window_takes_only_what_is_in_play():
    """Fifteen months back from a February night: this season, the playoffs it
    runs into, and next season the moment the feed lists it."""
    earliest = date(2026, 2, 1) - timedelta(days=RECENT_SEASON_DAYS)
    assert ids(in_scope(SEASONS, earliest=earliest, only=None)) == ["70", "69", "65"]


def test_the_window_is_inclusive_of_its_own_edge():
    on_the_line = date(2025, 9, 19)
    assert "65" in ids(in_scope(SEASONS, earliest=on_the_line, only=None))
    assert "65" not in ids(in_scope(SEASONS, earliest=date(2025, 9, 20), only=None))


def test_a_season_with_no_start_date_is_left_alone():
    """It can't be placed, and guessing would either read it every night or
    never read it at all."""
    undated = [season("99", None)]
    assert in_scope(undated, earliest=date(1990, 1, 1), only=None) == []


def test_but_it_can_still_be_asked_for_by_name():
    undated = [season("99", None)]
    assert ids(in_scope(undated, earliest=date(2026, 1, 1), only="99")) == ["99"]


@pytest.mark.parametrize("earliest", [date(2019, 1, 1), date(2030, 1, 1)])
def test_nothing_in_nothing_out(earliest):
    assert in_scope([], earliest=earliest, only=None) == []


class TestIsCompetition:
    """Every name here is one the feed has actually served."""

    @pytest.mark.parametrize(
        "name",
        [
            "2025/26 Regular Season",
            "2025 - 26 Regular Season",  # WHL
            "2025-26 | Regular Season",  # QMJHL
            "2023-24 AB Regular Season",  # BCHL, split by province that year
            "2026 WHL Playoffs",
            "2025-26 Playoffs",
            "2022 | Playoffs",  # QMJHL
            "2024 Mowat Cup",  # a provincial championship — real hockey
            "2023 Cyclone Taylor Cup",
        ],
    )
    def test_games_played_for_something_are_kept(self, name):
        assert is_competition(season("1", "2025-09-01", name))

    @pytest.mark.parametrize(
        "name",
        [
            "2025 - 26 Pre-Season",  # WHL
            "2025 Pre-Season",  # OHL
            "2022 Pre-season",  # OHL, lowercased that year
            "Pre-Season 2025",  # QMJHL
            "2025/26 Exhibition",  # KIJHL
            "2026 Exhibition Season",  # PJHL
            "2026 All-Star Weekend",  # BCHL
            "2025-26 OHL Top Prospects",
            "WHL Prospects Game 2026",
            "2023 BCHC Prospects Game",
            "Test Season 2026",  # the training client's sandbox
        ],
    )
    def test_the_rest_are_not(self, name):
        assert not is_competition(season("1", "2025-09-01", name))

    def test_the_playoff_flag_is_left_to_say_what_it_says(self):
        """It only separates playoffs from everything else, which is why the
        name is what decides this — but playoffs stay marked as playoffs."""
        playoffs = Season(id="67", name="2025-26 Playoffs", playoff=True, starts_on=None)
        assert is_competition(playoffs)
        assert playoffs.playoff
