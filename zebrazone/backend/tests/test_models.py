"""The two things the models work out for themselves."""

import pytest

from app.models import ROLE_BY_SLOT, Official


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
