# ZebraZone

Shows every game a hockey league played on a given day: the score, each team's
penalty minutes, the majors and misconducts behind them, and the crew who
worked the game.

Reads the HockeyTech (LeagueStat) feed that all their leagues share, so adding a
league is one line of config — the response shape is identical for every one.

## Running it

One command, from this directory:

```bash
npm install       # first time only, for the runner itself
npm run locally
```

It runs the two commands below side by side, labelling whose output is whose, and
Ctrl+C stops both. Their dependencies still have to be installed the first time.

Or a terminal each:

```bash
# backend  -> http://127.0.0.1:8100
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8100
```

Linting is `ruff check app` and `ruff format app`, tests are `pytest` (both
`pip install -r requirements-dev.txt`); the frontend's linting is `npm run lint`.

```bash
# frontend -> http://localhost:5173
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to the backend, so the frontend
uses relative URLs and needs no CORS setup.

## The database

Only the pages built on history need one — the games page reads the feed
directly, and without `DATABASE_URL` the app runs fine and says so plainly if
you ask it for a statistic.

```bash
docker compose up -d --wait     # Postgres, with the schema already applied
export DATABASE_URL=postgresql://zebrazone:zebrazone@localhost:5432/zebrazone
```

`docker compose down` stops it and keeps the data; `down -v` throws the data
away. Any Postgres will do if you'd rather not use Docker — the schema is
`backend/app/schema.sql` and `ingest` applies it itself.

Then fill it from the feed:

```bash
cd backend
python -m app.ingest --league kijhl --season 65   # one season, a minute or so
python -m app.ingest --recent                     # the seasons in play
python -m app.ingest                              # everything since 2022
```

The last is some sixteen thousand games and around twenty minutes, which is why
this is a command and not an endpoint: nothing a page view can set off.

`--recent` is the one to schedule. It reads the seasons that started in the last
fifteen months — the season being played, the playoffs it runs into, and next
season from the day the feed lists it — and skips every game whose change stamp
hasn't moved since we last read it. With nothing new that's about forty requests
and half a minute; a night with games costs one summary each on top.

A summary that won't load is asked for again for a fortnight, because they do
sometimes lag a game by a day or two. After that it's left alone: a league whose
key can't read the view at all would otherwise be re-asked for every game it
has, every night, forever.

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
  nav.ts          the pages a league has, and which one the URL is asking for
  App.tsx         Controller — the chosen league, and which page is showing
  pages/          one per page: Home picks a league, Games lists a day's games
  components/     View — presentation only
  assets/leagues/ league logos, each named after its league's id
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
    tier=Tier.MAJOR,
),
```

It appears in the picker automatically, under its tier and themed in its `accent`
colour. No parsing code to write — every HockeyTech league returns the same
structure. Entries can sit anywhere in `LEAGUES`: `/api/leagues` sorts by tier,
and the picker groups by taking the order it's handed.

Its logo is a file in `frontend/src/assets/leagues` named after the id —
`whl.svg`, `ohl.png`, `bchc.webp`, whichever format you have. Vite resolves the
folder at build time, so nothing else needs telling; a league without one shows
an empty ring in its place.

Add `visible=False` to keep a league out of the picker while you check it. It
stays reachable at `/api/games?league=<id>`, so an unfinished league can be
tried without being announced.

A key is scoped to one client code and is cleared for some feed views but not
others, which is not something you can tell by looking at it. The WIJHL's key,
for instance, reads schedules but not game summaries, so its games show scores
and no penalty data. That degrades quietly rather than failing — but if a
league shows less than you expect, that's the reason, and `GET /api/games` will
say `Feed type access denied` if the refusal is total.

## Choosing a league

The homepage is the picker, grouped by tier, and the base URL always lands there.
Picking a league opens its games; the bar at the top changes it afterwards
without leaving the page you're on. Either way the choice is kept in
`sessionStorage`, so it holds across reloads and page changes and is asked for
again the next time the app is opened fresh.

Pages sit behind a hash — `#games`, `#officials` — which is all the routing this
needs: the address bar and the back button both work, with no router. It lives in
`nav.ts` beside the list of pages, and a hash asking for a page before a league
is chosen lands on the picker instead.

## Look and feel

Black-and-white referee stripes trim the top and bottom of the page, and the
selected league's armband colour — orange for the WHL, red for the KIJHL —
accents everything else. That colour is the `accent` field above: the frontend
reads it from `/api/leagues` and sets the `--armband` CSS variable on `<html>`,
so the palette has one source of truth and no per-league CSS.

`App.css` is the shell and what every page reuses — the masthead and colophon,
`main`, `.card`, a filter row, a message. Anything belonging to one page or one
component is a stylesheet beside it (`Home.css`, `Navbar.css`, `GameCard.css`),
imported there, so a page's look travels with the page.

`.card` is the piece worth knowing: a sheet of paper with a coloured left edge
that slides under the pointer. Its edge is `--edge`, black by default and the
armband on hover; the league picker's cards set both inline to the league's own
colour, so they keep it throughout.

Built mobile first. Each stylesheet reads as a phone stylesheet with one
`min-width: 600px` block adding room on bigger screens, and nothing is allowed
to scroll sideways at any width.

The feed carries no team colours, only logos, so a team is identified by its
crest with its three-letter code as the fallback.

## The API

| Endpoint | Returns |
|---|---|
| `GET /api/leagues` | `[{ id, name, accent, tier }]`, major junior first |
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
