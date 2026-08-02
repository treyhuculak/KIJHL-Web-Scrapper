"""Which leagues the app knows about."""

from pydantic import BaseModel


class LeagueConfig(BaseModel):
    """A league on the HockeyTech platform."""

    id: str
    name: str
    client_code: str
    api_key: str
    accent: str
    """The league's armband colour — the page is themed with it."""
    visible: bool = True
    """Whether to offer this league publicly. A hidden league stays out of the
    picker but can still be reached at /api/games?league=<id>, so one that
    isn't ready yet can be checked without being announced."""


COLOURS = {
    "orange": "#e06900",
    "red": "#cc0000",
}

# Every HockeyTech league serves the same feed, so a league needs nothing but
# its credentials and a colour. To add one, add a line here; add visible=False
# to keep it out of the picker until it's ready.
LEAGUES: dict[str, LeagueConfig] = {
    "whl": LeagueConfig(
        id="whl",
        name="Western Hockey League",
        client_code="whl",
        api_key="f1aa699db3d81487",
        accent=COLOURS["orange"],
        visible=True,
    ),
    "ohl": LeagueConfig(
        id="ohl",
        name="Ontario Hockey League",
        client_code="ohl",
        api_key="f1aa699db3d81487",
        accent=COLOURS["orange"],
        visible=False,
    ),
    "qmjhl": LeagueConfig(
        id="qmjhl",
        name="Quebec Major Junior Hockey League",
        client_code="lhjmq",
        api_key="f1aa699db3d81487",
        accent=COLOURS["orange"],
        visible=False,
    ),
    "bchc": LeagueConfig(
        id="bchc",
        name="British Columbia Hockey Conference",
        client_code="hockeytechtraining",
        api_key="60926b45222d54eb",
        accent=COLOURS["red"],
        visible=True,
    ),
    "pjhl": LeagueConfig(
        id="pjhl",
        name="Pacific Junior Hockey League",
        client_code="pjhlbc",
        api_key="5e5fc2923094641d",
        accent=COLOURS["red"],
        visible=True,
    ),
    "bchl": LeagueConfig(
        id="bchl",
        name="British Columbia Hockey League",
        client_code="bchl",
        api_key="f3ed30007ad2124e",
        accent=COLOURS["orange"],
        visible=False,
    ),
    "wijhl": LeagueConfig(
        id="wijhl",
        name="Western International Junior Hockey League",
        client_code="wijhl",
        api_key="44808f115c1b5263",
        accent=COLOURS["orange"],
        visible=False,
    ),
    "kijhl": LeagueConfig(
        id="kijhl",
        name="Kootenay International Junior Hockey League",
        client_code="kijhl",
        api_key="2589e0f644b1bb71",
        accent=COLOURS["red"],
        visible=False,
    ),
}
