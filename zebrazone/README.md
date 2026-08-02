# ZebraZone

Shows every game a hockey league played on a given day.

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
  models.py       Model  — League, Team, Game
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

## Adding a league

Add an entry to `LEAGUES` in `backend/app/config.py`:

```python
"whl": LeagueConfig(
    id="whl",
    name="Western Hockey League",
    client_code="whl",
    api_key="f1aa699db3d81487",
),
```

It appears in the dropdown automatically. No parsing code to write — every
HockeyTech league returns the same structure.

## The API

| Endpoint | Returns |
|---|---|
| `GET /api/leagues` | `[{ id, name }]` |
| `GET /api/games?league=whl&date=2026-01-10` | `[{ id, date, status, venue, start_time, attendance, home, visitor }]` |

Interactive docs while the backend runs: http://127.0.0.1:8100/docs
