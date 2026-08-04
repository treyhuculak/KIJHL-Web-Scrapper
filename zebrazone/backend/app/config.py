"""Which leagues the app knows about."""

import os
from pathlib import Path

from pydantic import BaseModel

from .models import Tier

ENV_FILE = Path(__file__).parent.parent / ".env"


def _read_env_file() -> None:
    """Fill in what the environment hasn't already said.

    Keeps a checkout's DATABASE_URL beside the code instead of in whichever
    shell started the server. A real environment variable always wins, so
    production, where there is no file, is unaffected.
    """
    if not ENV_FILE.exists():
        return

    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        setting = line.strip()
        if not setting or setting.startswith("#") or "=" not in setting:
            continue
        name, value = setting.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


_read_env_file()

DATABASE_URL = os.environ.get("DATABASE_URL", "")
"""Where the seasons of history live — Neon's pooled endpoint in production.

Empty in a checkout that hasn't been pointed at one, which is a working state:
the games page reads the feed directly, and only the pages built on history
need this.
"""

BACKFILL_FROM = 2022
"""How far back to ingest. The feed reaches the 1990s for some leagues, but
officialsOnIce is sparse before 2016 and empty before that, and four seasons is
the history worth having. Leagues newer than this simply bring what they have.
"""

RECENT_SEASON_DAYS = 460
"""What `ingest --recent` looks at: seasons that started in the last fifteen
months. That's the season being played, the playoffs it runs into, and next
season from the day it appears — and none of the finished ones behind them,
which can't change and needn't be read every night.
"""

SUMMARY_RETRY_DAYS = 14
"""How long to keep asking for a summary that hasn't appeared. They can lag a
game by a day or two; past a fortnight one isn't coming, and a league whose key
can't read them at all would otherwise be re-asked for every game it has, every
night, forever.
"""


class LeagueConfig(BaseModel):
    """A league on the HockeyTech platform."""

    id: str
    name: str
    client_code: str
    api_key: str
    accent: str
    """The league's armband colour — the page is themed with it."""
    tier: Tier
    """The level it plays at. The league picker groups by this."""
    visible: bool = True
    """Whether to offer this league publicly. A hidden league stays out of the
    picker but can still be reached at /api/games?league=<id>, so one that
    isn't ready yet can be checked without being announced."""


COLOURS = {
    "orange": "#e06900",
    "red": "#cc0000",
}

# Every HockeyTech league serves the same feed, so a league needs nothing but
# its credentials, a colour and the level it plays at. To add one, add a line
# here; add visible=False to keep it out of the picker until it's ready.
#
# Grouped by tier to read by, but the picker sorts by tier itself — an entry can
# go anywhere in here.
LEAGUES: dict[str, LeagueConfig] = {
    "whl": LeagueConfig(
        id="whl",
        name="Western Hockey League",
        client_code="whl",
        api_key="f1aa699db3d81487",
        accent=COLOURS["orange"],
        tier=Tier.MAJOR,
        visible=True,
    ),
    "ohl": LeagueConfig(
        id="ohl",
        name="Ontario Hockey League",
        client_code="ohl",
        api_key="f1aa699db3d81487",
        accent=COLOURS["orange"],
        tier=Tier.MAJOR,
        visible=True,
    ),
    "qmjhl": LeagueConfig(
        id="qmjhl",
        name="Quebec Major Junior Hockey League",
        client_code="lhjmq",
        api_key="f1aa699db3d81487",
        accent=COLOURS["orange"],
        tier=Tier.MAJOR,
        visible=True,
    ),
    "bchc": LeagueConfig(
        id="bchc",
        name="British Columbia Hockey Conference",
        client_code="hockeytechtraining",
        api_key="60926b45222d54eb",
        accent=COLOURS["red"],
        tier=Tier.JUNIOR_A,
        visible=True,
    ),
    "bchl": LeagueConfig(
        id="bchl",
        name="British Columbia Hockey League",
        client_code="bchl",
        api_key="f3ed30007ad2124e",
        accent=COLOURS["orange"],
        tier=Tier.JUNIOR_A,
        visible=True,
    ),
    "pjhl": LeagueConfig(
        id="pjhl",
        name="Pacific Junior Hockey League",
        client_code="pjhlbc",
        api_key="5e5fc2923094641d",
        accent=COLOURS["red"],
        tier=Tier.JUNIOR_B,
        visible=True,
    ),
    "wijhl": LeagueConfig(
        id="wijhl",
        name="Western International Junior Hockey League",
        client_code="wijhl",
        api_key="44808f115c1b5263",
        accent=COLOURS["orange"],
        tier=Tier.JUNIOR_B,
        visible=True,
    ),
    "kijhl": LeagueConfig(
        id="kijhl",
        name="Kootenay International Junior Hockey League",
        client_code="kijhl",
        api_key="2589e0f644b1bb71",
        accent=COLOURS["red"],
        tier=Tier.JUNIOR_B,
        visible=True,
    ),
}
