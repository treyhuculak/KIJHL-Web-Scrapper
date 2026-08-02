# ZebraZone

Shows every game a hockey league played on a given day: the score, each team's
penalty minutes, the majors and misconducts behind them, and the crew who
worked the game.

Reads the HockeyTech (LeagueStat) feed that all their leagues share, so adding a
league is one line of config — the response shape is identical for every one.

## Running it

Two terminals.

```bash
# backend  -> http://127.0.0.1:8100
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8100
```

Linting is `ruff check app` and `ruff format app` (`pip install -r
requirements-dev.txt`); the frontend's is `npm run lint`.

```bash
# frontend -> http://localhost:5173
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to the backend, so the frontend
uses relative URLs and needs no CORS setup.

## Layout

```
backend/app/
  config.py       the leagues we support
  models.py       Model  — League, Team, Penalty, Game
  hockeytech.py   Model  — the only code that knows the upstream API
  routes.py       Controller — GET /api/leagues, GET /api/games
  main.py         wiring

frontend/src/
  api.ts          Model — types + the two calls to the backend
  App.tsx         Controller — holds state, decides what to fetch
  components/     View — presentation only
```

The rule that keeps this honest: `hockeytech.py` is the single place that knows
the feed's field names. Everything above it works with `Game` and `Team`. If the
upstream API changes, one file changes.

Three of the feed's views go into a day's games, and `hockeytech.py` requests
them all concurrently:

| View | Gives us |
|---|---|
| `modulekit / gamesbydate` | the day's games, teams and scores |
| `gc / gamesummary` | penalty minutes per team, and every penalty called |
| `modulekit / teamsbyseason` | team logo URLs |

The summary is per game, so a day costs one request per game plus two. Every one
of these views answers with the same shape for every league — the old habit of
picking a different endpoint per league was never necessary.

## Adding a league

Add an entry to `LEAGUES` in `backend/app/config.py`:

```python
"whl": LeagueConfig(
    id="whl",
    name="Western Hockey League",
    client_code="whl",
    api_key="f1aa699db3d81487",
    accent="#e06900",
),
```

It appears in the dropdown automatically, themed in its `accent` colour. No
parsing code to write — every HockeyTech league returns the same structure.

Add `visible=False` to keep a league out of the picker while you check it. It
stays reachable at `/api/games?league=<id>`, so an unfinished league can be
tried without being announced.

A key is scoped to one client code and is cleared for some feed views but not
others, which is not something you can tell by looking at it. The WIJHL's key,
for instance, reads schedules but not game summaries, so its games show scores
and no penalty data. That degrades quietly rather than failing — but if a
league shows less than you expect, that's the reason, and `GET /api/games` will
say `Feed type access denied` if the refusal is total.

## Look and feel

Black-and-white referee stripes trim the top and bottom of the page, and the
selected league's armband colour — orange for the WHL, red for the KIJHL —
accents everything else. That colour is the `accent` field above: the frontend
reads it from `/api/leagues` and sets the `--armband` CSS variable on `<html>`,
so the palette has one source of truth and no per-league CSS.

Built mobile first. `App.css` reads as a phone stylesheet with one
`min-width: 600px` block adding room on bigger screens, and nothing is allowed
to scroll sideways at any width.

The feed carries no team colours, only logos, so a team is identified by its
crest with its three-letter code as the fallback.

## The API

| Endpoint | Returns |
|---|---|
| `GET /api/leagues` | `[{ id, name, accent }]` |
| `GET /api/games?league=whl&date=2026-01-10` | `[{ id, date, status, final, venue, start_time, attendance, home, visitor, notable_penalties, officials }]` |

`home` and `visitor` are `{ code, city, nickname, goals, pims, logo }`.

`notable_penalties` holds the majors and misconducts as
`{ team_code, player, infraction, minutes, period, time }` — minors are counted
in `pims` but not listed.

`officials` is the on-ice crew as `{ name, role, number }`. The feed labels them
'Referee 1', 'Linesman 2' and so on; `hockeytech.py` drops the slot number and
renames the role to linesperson, so nothing downstream sees the feed's wording.
`number` is null in leagues that don't number their officials — the KIJHL sends
a zero for all four.

Interactive docs while the backend runs: http://127.0.0.1:8100/docs
