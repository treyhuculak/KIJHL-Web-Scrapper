"""What the feed reader makes of the feed.

Every fixture here is shaped like something the real feed has actually sent —
the four spellings of a fighting major, a misconduct filed under its own class,
a jersey number of zero standing in for a league that doesn't number its
officials. No test reaches the network: these are the rules we apply to what
comes back, and they should be checkable without asking anyone for anything.
"""

import httpx
import pytest

from app.hockeytech import (
    AGAIN_LATER,
    FeedUnavailable,
    _count_majors,
    _number,
    _read_game,
    _read_officials,
    _read_penalty,
    _read_scheduled,
    _read_summary,
    _transient,
)


def fighting(home: str, seconds: int, period: str = "1", wording: str = "Major-Fighting") -> dict:
    return {
        "penalty_class": "Major",
        "lang_penalty_description": wording,
        "home": home,
        "s": seconds,
        "period_id": period,
    }


def penalty(penalty_class: str, description: str, home: str = "1", seconds: int = 100) -> dict:
    return {
        "penalty_class": penalty_class,
        "lang_penalty_description": description,
        "home": home,
        "s": seconds,
        "period_id": "1",
        "minutes": 5,
        "period": "1st",
        "time_off_formatted": "1:40",
    }


class TestCountMajors:
    """A fight is an exchange, not a penalty. Everything here is that rule."""

    def test_nothing_called(self):
        assert _count_majors([]) == (0, 0)

    def test_minors_are_not_majors(self):
        minors = [penalty("Minor", "Hooking"), penalty("Double Minor", "High Sticking")]
        assert _count_majors(minors) == (0, 0)

    def test_two_sides_at_one_stoppage_is_one_fight(self):
        assert _count_majors([fighting("0", 886), fighting("1", 886)]) == (0, 1)

    def test_four_at_one_stoppage_is_two_fights(self):
        """Seen once in forty WHL games: two fights breaking out together."""
        brawl = [fighting("0", 303), fighting("1", 303), fighting("0", 303), fighting("1", 303)]
        assert _count_majors(brawl) == (0, 2)

    def test_a_lone_fighting_major_is_a_major(self):
        """Nobody fought back — a player jumped, or an aggressor. Not a fight."""
        assert _count_majors([fighting("0", 176)]) == (1, 0)

    def test_three_against_one_pairs_off_what_it_can(self):
        crowd = [fighting("0", 90), fighting("0", 90), fighting("0", 90), fighting("1", 90)]
        assert _count_majors(crowd) == (2, 1)

    def test_separate_stoppages_are_separate_fights(self):
        two = [fighting("0", 100), fighting("1", 100), fighting("0", 500), fighting("1", 500)]
        assert _count_majors(two) == (0, 2)

    def test_same_clock_in_different_periods_is_not_one_stoppage(self):
        """The period clock restarts, so seconds alone would merge these two."""
        both = [
            fighting("0", 240, period="1"),
            fighting("1", 240, period="1"),
            fighting("0", 240, period="3"),
            fighting("1", 240, period="3"),
        ]
        assert _count_majors(both) == (0, 2)

    @pytest.mark.parametrize(
        "wording",
        [
            "Fighting",  # BCHL
            "Major-Fighting",  # WHL
            "Fighting - Major (5 Minutes)",  # KIJHL, PJHL
            "FIGHTING",  # nobody yet, but the match is case-insensitive
        ],
    )
    def test_every_spelling_of_fighting_is_recognised(self, wording):
        pair = [fighting("0", 400, wording=wording), fighting("1", 400, wording=wording)]
        assert _count_majors(pair) == (0, 1)

    def test_match_penalties_count_as_majors(self):
        assert _count_majors([penalty("Match", "Match Penalty")]) == (1, 0)

    def test_misconducts_are_neither(self):
        """They're serious, but they aren't majors and they aren't fights. The
        BCHL files game misconducts under a class of their own."""
        calls = [
            penalty("Misconduct", "Misconduct (10 Minutes)"),
            penalty("Game Misconduct", "Game Misconduct"),
            penalty("Misconduct", "Game Misconduct - Fighting Rule 46"),
        ]
        assert _count_majors(calls) == (0, 0)

    def test_a_fight_and_an_ordinary_major_together(self):
        mixed = [
            fighting("0", 600),
            fighting("1", 600),
            penalty("Major", "Checking From Behind - Major (5 Minutes)"),
        ]
        assert _count_majors(mixed) == (1, 1)


class TestReadOfficials:
    def crew_member(self, **overrides) -> dict:
        entry = {
            "official_type_id": "1",
            "description": "Referee 1",
            "first_name": "Gerald",
            "last_name": "Hofferd",
            "jersey_number": "12",
            "person_id": "672",
        }
        return {**entry, **overrides}

    def test_a_full_crew(self):
        summary = {
            "officialsOnIce": [
                self.crew_member(official_type_id="1", person_id="1"),
                self.crew_member(official_type_id="2", person_id="2"),
                self.crew_member(official_type_id="3", person_id="3"),
                self.crew_member(official_type_id="4", person_id="4"),
            ]
        }
        crew = _read_officials(summary)
        assert [o.role for o in crew] == ["Referee", "Referee", "Linesperson", "Linesperson"]
        assert [o.person_id for o in crew] == ["1", "2", "3", "4"]

    def test_a_crew_of_three(self):
        """One WHL game in forty had one. Nothing may assume a crew of four."""
        summary = {
            "officialsOnIce": [
                self.crew_member(official_type_id="1", person_id="1"),
                self.crew_member(official_type_id="3", person_id="3"),
                self.crew_member(official_type_id="4", person_id="4"),
            ]
        }
        assert len(_read_officials(summary)) == 3

    def test_no_crew_at_all(self):
        assert _read_officials({}) == []
        assert _read_officials({"officialsOnIce": []}) == []

    def test_a_zero_jersey_is_no_jersey(self):
        """The KIJHL numbers none of its officials and sends 0 for all four."""
        crew = _read_officials({"officialsOnIce": [self.crew_member(jersey_number="0")]})
        assert crew[0].number is None

    def test_a_real_jersey_survives(self):
        crew = _read_officials({"officialsOnIce": [self.crew_member(jersey_number="12")]})
        assert crew[0].number == 12

    def test_an_official_with_no_id_is_dropped(self):
        """There would be nothing to count them under."""
        assert _read_officials({"officialsOnIce": [self.crew_member(person_id="")]}) == []

    def test_a_nameless_official_is_dropped(self):
        nameless = self.crew_member(first_name="", last_name="")
        assert _read_officials({"officialsOnIce": [nameless]}) == []

    def test_one_name_is_enough(self):
        crew = _read_officials({"officialsOnIce": [self.crew_member(first_name="")]})
        assert crew[0].name == "Hofferd"

    def test_an_unfamiliar_slot_is_not_guessed_at(self):
        crew = _read_officials({"officialsOnIce": [self.crew_member(official_type_id="9")]})
        assert crew[0].role == "Official"

    def test_the_feed_is_not_tidied_on_the_way_in(self):
        """Some names arrive lowercase. Storing them as sent keeps the feed's
        word; presentation is the page's business."""
        crew = _read_officials({"officialsOnIce": [self.crew_member(first_name="brendan")]})
        assert crew[0].name == "brendan Hofferd"


class TestReadSummary:
    def test_an_unreadable_summary_says_nothing(self):
        """Not zero. A league whose key can't read the view has not just
        watched a game in which nobody took a penalty."""
        summary = _read_summary({})
        assert summary.home_pims is None
        assert summary.visitor_pims is None
        assert summary.majors is None
        assert summary.fights is None
        assert summary.officials == []

    def test_a_clean_game_says_zero(self):
        summary = _read_summary({"pimTotal": {"home": "0", "visitor": "0"}, "penalties": []})
        assert (summary.home_pims, summary.visitor_pims) == (0, 0)
        assert (summary.majors, summary.fights) == (0, 0)

    def test_minutes_and_counts_together(self):
        summary = _read_summary(
            {
                "pimTotal": {"home": "29", "visitor": "17"},
                "penalties": [fighting("0", 700), fighting("1", 700), penalty("Minor", "Tripping")],
            }
        )
        assert (summary.home_pims, summary.visitor_pims) == (29, 17)
        assert (summary.majors, summary.fights) == (0, 1)


class TestReadPenalty:
    def test_the_home_flag_decides_the_team(self):
        """It's set for bench penalties too, where the player's team isn't."""
        home = _read_penalty(penalty("Major", "Slashing", home="1"), "COL", "GOL")
        visiting = _read_penalty(penalty("Major", "Slashing", home="0"), "COL", "GOL")
        assert (home.team_code, visiting.team_code) == ("COL", "GOL")

    def test_a_penalty_nobody_is_named_for_is_the_bench(self):
        assert _read_penalty(penalty("Minor", "Too Many Men"), "COL", "GOL").player == "Bench"

    def test_whoever_served_it_when_nobody_took_it(self):
        served = penalty("Minor", "Too Many Men") | {
            "player_served_info": {"first_name": "Ethan", "last_name": "McLean"}
        }
        assert _read_penalty(served, "COL", "GOL").player == "Ethan McLean"

    def test_the_player_penalised_comes_first(self):
        both = penalty("Major", "Fighting") | {
            "player_penalized_info": {"first_name": "Nolan", "last_name": "Lamond"},
            "player_served_info": {"first_name": "Someone", "last_name": "Else"},
        }
        assert _read_penalty(both, "COL", "GOL").player == "Nolan Lamond"


class TestReadGame:
    def entry(self, **overrides) -> dict:
        row = {
            "id": "19008",
            "date_played": "2026-01-10",
            "game_status": "Final",
            "venue": "Eddie Mountain Memorial Arena",
            "home_team_code": "COL",
            "visiting_team_code": "GOL",
            "home_goal_count": "2",
            "visiting_goal_count": "5",
            "home_team": "1",
            "visiting_team": "2",
            "attendance": "412",
        }
        return {**row, **overrides}

    @pytest.mark.parametrize("status", ["Final", "Final OT", "Final SO"])
    def test_a_finished_game_is_final(self, status):
        assert _read_game(self.entry(game_status=status), {}, {}).final

    def test_a_game_still_to_come_is_not(self):
        """One yet to be played carries its start time where a status would be."""
        assert not _read_game(self.entry(game_status="6:05 pm PDT"), {}, {}).final

    def test_an_unread_summary_leaves_penalty_minutes_unknown(self):
        game = _read_game(self.entry(), {}, {})
        assert game.home.pims is None
        assert game.visitor.pims is None

    def test_the_routine_calls_are_left_off_the_card(self):
        summary = {
            "penalties": [
                penalty("Minor", "Hooking"),
                penalty("Double Minor", "High Sticking"),
                penalty("Major", "Fighting"),
                penalty("Match", "Match Penalty"),
                penalty("Misconduct", "Misconduct (10 Minutes)"),
                penalty("Game Misconduct", "Game Misconduct"),
            ]
        }
        listed = [p.infraction for p in _read_game(self.entry(), summary, {}).notable_penalties]
        assert listed == ["Fighting", "Match Penalty", "Misconduct (10 Minutes)", "Game Misconduct"]

    def test_logos_are_looked_up_by_team_id(self):
        game = _read_game(self.entry(), {}, {"1": "https://example.test/col.png"})
        assert game.home.logo == "https://example.test/col.png"
        assert game.visitor.logo == ""


class TestReadScheduled:
    def test_a_schedule_row_becomes_a_record(self):
        row = {
            "id": "1022126",
            "date_played": "2025-09-19",
            "home_team_code": "BDN",
            "visiting_team_code": "MJ",
            "home_goal_count": "4",
            "visiting_goal_count": "6",
            "last_modified": "2025-10-15 08:42:34",
        }
        record = _read_scheduled(row, season_id="289")
        assert record.id == "1022126"
        assert record.season_id == "289"
        assert record.played_on.isoformat() == "2025-09-19"
        assert (record.home_goals, record.visitor_goals) == (4, 6)
        assert record.last_modified == "2025-10-15 08:42:34"

    def test_the_summary_is_empty_until_it_is_read(self):
        row = {"id": "1", "date_played": "2025-09-19"}
        assert _read_scheduled(row, "289").summary.home_pims is None


@pytest.mark.parametrize(
    ("sent", "expected"),
    [
        (5, 5),
        ("5", 5),
        ("0", 0),
        (0, 0),
        ("", None),
        (None, None),
        ("TBD", None),
        ("1,024", None),
    ],
)
def test_number_takes_what_the_feed_sends(sent, expected):
    """Numbers arrive as ints, as strings, and as blanks where none was given."""
    assert _number(sent) == expected


class TestWhatIsWorthAskingTwice:
    """Which failures a backfill should sit out and which it should give up on.

    The first full backfill died on a connect timeout with one league read and
    seven to go, which is what the retry is for. What it must not do is retry
    the feed's own refusals — a key that isn't cleared for a view says so for
    every game in the league, and waiting two seconds each time would turn a
    quiet degradation into an hour of nothing.
    """

    def _refused(self, status: int) -> httpx.HTTPStatusError:
        request = httpx.Request("GET", "https://example.test/feed/")
        return httpx.HTTPStatusError(
            f"{status}", request=request, response=httpx.Response(status, request=request)
        )

    @pytest.mark.parametrize(
        "error",
        [
            httpx.ConnectTimeout("timed out"),
            httpx.ReadTimeout("timed out"),
            httpx.ConnectError("refused"),
            httpx.PoolTimeout("no connection free"),
        ],
    )
    def test_a_connection_that_never_happened_is_worth_another_go(self, error):
        assert _transient(error)

    @pytest.mark.parametrize("status", sorted(AGAIN_LATER))
    def test_a_server_having_a_moment_is_too(self, status):
        assert _transient(self._refused(status))

    @pytest.mark.parametrize("status", [400, 401, 403, 404, 410, 422])
    def test_but_a_refusal_means_the_same_thing_every_time(self, status):
        assert not _transient(self._refused(status))

    def test_and_the_feed_saying_no_at_200_is_an_answer_not_a_failure(self):
        """'Feed type access denied.' with an HTTP 200 body — the WIJHL's key
        does this for every game summary it has. Retrying it would cost two
        seconds a game to learn what it said the first time."""
        assert not _transient(FeedUnavailable("Feed type access denied."))
