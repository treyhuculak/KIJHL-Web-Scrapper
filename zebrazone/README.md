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
```

The connection string lives in `backend/.env`, which is git-ignored and read at
startup — so it doesn't matter which shell you run things from, and forgetting
to export it can't quietly turn into a page saying there's no history. A real
`DATABASE_URL` in the environment always wins over the file, which is how
production gets its Neon one. Anything that builds an image from `backend/`
must exclude `.env`.

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
  models.py       Model  — League, Team, Penalty, Game, and the stored ones
  hockeytech.py   Model  — the only code that knows the upstream API
  store.py        Model  — the only code that knows SQL
  schema.sql      the four tables
  ingest.py       the command that fills them from the feed
  routes.py       Controller — the five GETs below
  main.py         wiring

frontend/src/
  api.ts          Model — types + the calls to the backend
  nav.ts          the pages a league has, and which one the URL is asking for
  seasons.ts      the season being looked at, shared by the pages built on history
  App.tsx         Controller — the chosen league, and which page is showing
  pages/          Home picks a league, Games a day, Officials and Stats a season
  components/     View — presentation only
  assets/leagues/ league logos, each named after its league's id
```

The rule that keeps this honest: `hockeytech.py` is the single place that knows
the feed's field names, and `store.py` the single place that knows SQL.
Everything above the two of them works with `Game`, `Season` and
`OfficialSeason`. If the upstream API changes one file changes; if the database
does, one other file changes.

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

Pages sit behind a hash — `#games`, `#officials`, `#stats` — which is all the
routing this needs: the address bar and the back button both work, with no
router. It lives in `nav.ts` beside the list of pages, and a hash asking for a
page before a league is chosen lands on the picker instead.

The way back to the picker is the wordmark, not a tab. Three pages and the
league select is already 383px of a 390px phone, and a Home tab would be another
74; the wordmark is where a reader looks for it anyway. The tabs scroll sideways
inside the bar if a narrower phone or a fourth page runs them out of room, which
is why `.navbar` is `nowrap` and `.tabs` is `min-width: 0` — a flex item won't
shrink under its content without it, and a strip that can't shrink can't scroll.

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
`min-width: 600px` block adding room on bigger screens, and the page is never
allowed to scroll sideways at any width. The officials table is the one thing
wider than a phone, and it scrolls within itself rather than taking the page
with it.

The feed carries no team colours, only logos, so a team is identified by its
crest with its three-letter code as the fallback.

## The API

| Endpoint | Returns |
|---|---|
| `GET /api/leagues` | `[{ id, name, accent, tier }]`, major junior first |
| `GET /api/games?league=whl&date=2026-01-10` | `[{ id, date, status, final, venue, start_time, attendance, home, visitor, notable_penalties, officials }]` |
| `GET /api/seasons?league=whl` | `[{ id, name, playoff, starts_on }]`, the one being played first |
| `GET /api/officials?league=whl&season=293` | `[{ person_id, name, number, role, games, pims, pims_per_game, majors, fights }]`, busiest first |
| `GET /api/stats?league=whl&season=293` | `{ fights, majors, wildest, referee_pairs, line_pairs }` — a season's standouts, five rows each |

The first two read the feed; the last three read the database, and answer `503`
rather than an error when there isn't one — nothing is wrong with the request
and the answer may exist tomorrow.

`home` and `visitor` are `{ code, city, nickname, goals, pims, logo }`.

`notable_penalties` holds the majors and misconducts as
`{ team_code, player, infraction, minutes, period, time }` — minors are counted
in `pims` but not listed.

`officials` is the on-ice crew as `{ name, role, number }`. The feed labels them
'Referee 1', 'Linesman 2' and so on; `hockeytech.py` drops the slot number and
renames the role to linesperson, so nothing downstream sees the feed's wording.
`number` is null in leagues that don't number their officials — the KIJHL sends
a zero for all four.

## The officials page

One season at a time, and one league at a time. The season picker holds the
seasons we actually have games for, freshest first, and opens on the one being
played — which is the season of the most recent game, so it moves to the
playoffs of its own accord when they start and to next season when that does.
Playoffs are a season of their own here, as they are upstream, so no figure on
the page is ever an average across two competitions.

Every column of figures sorts, at any width. A phone gets the same six columns
in short form and scrolls the table sideways inside itself rather than wrapping
names; the headings stick under the navbar on wider screens, where the table
always fits and so nothing is scrolling for them to stick to instead.

`role` is the job they did over the whole season rather than on one night, and
it's `Referee`, `Linesperson` or `Both`. Officials swap: never in major junior,
but a third of the KIJHL's roster works each job at some point. `Both` needs a
fifth of their nights on each — see `BOTH_JOBS_SHARE` in `models.py` — because
covering one game when someone is short isn't a second job, and counting it as
one put a quarter of that roster under `Both` on the strength of a single night.

On screen it's one pill either way: the armband colour for a referee, black for
the lines, and grey saying 50/50 for `Both`, since someone who is half of each
is neither. Those are the API's words translated for the reader, the way
`Linesperson` has always been shown as `Lines`. The role filter offers the same
three: either job includes the 50/50 officials, and asking for 50/50 leaves
only them.

## The stats page

The same season, asked a different question. Where the officials page is every
official and every figure, this is the top five of one figure at a time: the
lines who broke up the most fights, the referees with the most majors in their
games, the season's heaviest nights with the crew who had them, and the pairs
of referees and of linespersons put together most often.

Pairs, not crews, and that's the finding rather than a simplification. An exact
foursome almost never works together twice — 462 KIJHL games last season
produced 435 distinct crews, and the most any one of them repeated was three —
while two referees are put together eight or nine times. Every league behaves
this way; the OHL managed 674 crews in 681 games. A crew leaderboard would be a
list of one-offs sorted by luck.

Every board carries a rate beside its total, because whoever saw the most of
something has usually also worked the most nights. Some of those rates are
real and some aren't: over a full season the top referee for majors sits four
standard errors above the league's average, which no amount of scheduling
explains, while the top pairing's penalty minutes are a five-game average
against a spread of 37 and mean nothing at all.

And the caveat the page prints under itself: these count what happened in the
games an official worked, not what they called. The feed names the crew and it
names the penalties; it never says which of the four blew the whistle. Fixing
that needs the penalty rows stored per game, which they currently aren't.

Interactive docs while the backend runs: http://127.0.0.1:8100/docs
