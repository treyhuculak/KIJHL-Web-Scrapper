"""The things the models work out for themselves."""

import pytest

from app.models import ROLE_BY_SLOT, Official, role_for


def official(**overrides) -> Official:
    fields = {
        "person_id": "672",
        "first_name": "Gerald",
        "last_name": "Hofferd",
        "slot": 1,
        "number": None,
    }
    return Official(**{**fields, **overrides})


@pytest.mark.parametrize(
    ("slot", "role"),
    [(1, "Referee"), (2, "Referee"), (3, "Linesperson"), (4, "Linesperson")],
)
def test_the_role_comes_from_the_slot(slot, role):
    """Checked against every league that serves summaries before being relied on."""
    assert official(slot=slot).role == role


@pytest.mark.parametrize("slot", [0, 5, 99])
def test_an_unfamiliar_slot_is_not_guessed_at(slot):
    assert slot not in ROLE_BY_SLOT
    assert official(slot=slot).role == "Official"


def test_the_name_is_the_parts_put_together():
    assert official().name == "Gerald Hofferd"


@pytest.mark.parametrize(
    ("first", "last", "expected"),
    [("Gerald", "", "Gerald"), ("", "Hofferd", "Hofferd"), ("", "", "")],
)
def test_a_missing_part_leaves_no_stray_space(first, last, expected):
    assert official(first_name=first, last_name=last).name == expected


def test_both_are_sent_to_the_client():
    """The page reads `name` and `role`; nothing downstream should have to know
    they're worked out rather than stored."""
    sent = official(slot=3).model_dump()
    assert sent["name"] == "Gerald Hofferd"
    assert sent["role"] == "Linesperson"


class TestRoleForASeason:
    """A season's worth of slots, rather than one game's.

    One game has one slot and so one answer. A season is a count of nights on
    each job, and the question becomes which of them the official actually does.
    """

    @pytest.mark.parametrize("slots", [[1], [2], [1, 2], [1, 1, 2, 2, 1]])
    def test_a_season_of_refereeing_is_refereeing(self, slots):
        """Either referee slot, and both of them, are the same job."""
        assert role_for(slots) == "Referee"

    @pytest.mark.parametrize("slots", [[3], [4], [3, 4], [4, 3, 3, 4, 3]])
    def test_and_the_same_holds_on_the_lines(self, slots):
        assert role_for(slots) == "Linesperson"

    @pytest.mark.parametrize("slots", [[1, 3], [2, 4], [4, 1], [1, 2, 3, 4]])
    def test_an_even_split_is_both(self, slots):
        assert role_for(slots) == "Both"

    def test_the_order_slots_arrive_in_changes_nothing(self):
        assert role_for([3, 1]) == role_for([1, 3]) == "Both"


class TestWhereBothBegins:
    """The line between working both jobs and covering someone's night off.

    Drawn as a share of the nights worked rather than a number of them, so a
    six-game playoff run is judged the way a fifty-game season is.
    """

    def test_filling_in_once_is_not_a_second_job(self):
        """The case the threshold exists for. Sixteen KIJHL officials worked a
        single game on the other job last season; every one of them is a
        linesperson or a referee who helped out, not both."""
        assert role_for([3] * 40 + [1]) == "Linesperson"
        assert role_for([1] * 40 + [3]) == "Referee"

    def test_the_line_itself_counts_as_being_over_it(self):
        """Exactly a fifth — ten nights of fifty — is both. A tenth is not."""
        assert role_for([3] * 40 + [1] * 10) == "Both"
        assert role_for([3] * 45 + [1] * 5) == "Linesperson"

    def test_a_short_season_is_measured_the_same_way(self):
        """Two of six is a third of the work, which a threshold counted in
        games would have thrown away for no reason but the season being short."""
        assert role_for([3] * 4 + [1] * 2) == "Both"


class TestSlotsThatMeanNothing:
    @pytest.mark.parametrize("slots", [[7], [0, 9], []])
    def test_nothing_recognisable_is_not_guessed_at(self, slots):
        """Same rule as one game's: name it plainly rather than pick a side."""
        assert role_for(slots) == "Official"

    def test_an_unknown_slot_does_not_sway_the_jobs_beside_it(self):
        """It counts towards neither job and towards neither total, so it can't
        drag someone over or under the line."""
        assert role_for([1, 7]) == "Referee"
        assert role_for([3] * 40 + [1] * 10 + [7] * 50) == "Both"
