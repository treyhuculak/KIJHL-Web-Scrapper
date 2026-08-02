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


# Every HockeyTech league serves the same feed, so a league needs nothing but
# its credentials and a colour. To add one, add a line here.
LEAGUES: dict[str, LeagueConfig] = {
    "whl": LeagueConfig(
        id="whl",
        name="Western Hockey League",
        client_code="whl",
        api_key="f1aa699db3d81487",
        accent="#e06900",
    ),
    "kijhl": LeagueConfig(
        id="kijhl",
        name="Kootenay International Junior Hockey League",
        client_code="kijhl",
        api_key="2589e0f644b1bb71",
        accent="#cc0000",
    ),
}
