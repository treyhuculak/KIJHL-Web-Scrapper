-- The facts, not the statistics.
--
-- Nothing here stores a total, an average or a count across rows: those are
-- read out when a page asks for them. Aggregates that live in columns drift the
-- moment a game is re-read or a summary is amended, and they can only ever
-- answer the question you thought of when you wrote them. The per-game penalty
-- minutes are the exception that proves it — they're read straight off that one
-- game's summary and rewritten whenever it is, so there is nothing to drift.
--
-- Only games that have been played are stored, so there is no 'final' column —
-- a row existing is what that would have meant. Fixtures stay in the feed,
-- which the games page reads live.
--
-- Worth knowing before backfilling: the feed carries games back to 2005, but
-- officialsOnIce is empty until about 2016/17 and only complete from 2019/20.
-- Earlier seasons are games no officials page can ever show.
--
-- Leagues themselves stay in config.py; league_id is just the id from there.

CREATE TABLE IF NOT EXISTS season (
    league_id text NOT NULL,
    season_id text NOT NULL,
    name      text NOT NULL,
    -- Kept apart so a playoff run never quietly skews a regular season average.
    -- Cup tournaments arrive as seasons of their own too, a few games each.
    playoff   boolean NOT NULL,
    starts_on date,
    PRIMARY KEY (league_id, season_id)
);

CREATE TABLE IF NOT EXISTS game (
    league_id     text NOT NULL,
    game_id       text NOT NULL,
    season_id     text NOT NULL,
    played_on     date NOT NULL,
    home_code     text NOT NULL,
    visitor_code  text NOT NULL,
    home_goals    smallint,
    visitor_goals smallint,

    -- Penalty minutes per side. Null, not zero: a summary we could not read is
    -- not a penalty-free game, so an average has to exclude it rather than
    -- count it as clean. Null here is also what records that it went unread.
    home_pims     smallint,
    visitor_pims  smallint,

    -- Counts rather than minutes on purpose: the BCHL files its misconducts as
    -- zero minutes, so minutes don't compare between leagues. A call happening
    -- does.
    --
    -- majors — majors and match penalties, fighting aside.
    -- fights — an exchange, not a penalty: two players from opposite sides
    --          fighting at one stoppage is a single fight, and a fighting major
    --          with nobody opposite it counts as a major instead.
    majors        smallint,
    fights        smallint,

    -- The feed's own change marker. A nightly run compares it and asks only for
    -- the summaries of games that have actually moved — twenty-odd requests
    -- rather than every game of the past fortnight.
    last_modified text NOT NULL DEFAULT '',

    PRIMARY KEY (league_id, game_id)
);

CREATE TABLE IF NOT EXISTS official (
    league_id  text NOT NULL,
    -- The feed's own id for the person, so nothing depends on matching names.
    -- It is scoped to the league: the same human working two of them has two
    -- ids, and joining those up is a later problem with a table of its own.
    person_id  text NOT NULL,
    first_name text NOT NULL,
    last_name  text NOT NULL,
    -- As last seen. Leagues that don't number their officials send a zero,
    -- which is stored as null.
    number     smallint,
    PRIMARY KEY (league_id, person_id)
);

CREATE TABLE IF NOT EXISTS game_official (
    league_id text NOT NULL,
    game_id   text NOT NULL,
    person_id text NOT NULL,
    -- The feed's official_type_id: 1 and 2 are the referees, 3 and 4 the lines.
    -- The role reads off this, so it isn't stored twice.
    slot      smallint NOT NULL,
    PRIMARY KEY (league_id, game_id, person_id),
    FOREIGN KEY (league_id, game_id) REFERENCES game ON DELETE CASCADE,
    FOREIGN KEY (league_id, person_id) REFERENCES official ON DELETE CASCADE
);

-- A season's games, which is what every stat is drawn from.
CREATE INDEX IF NOT EXISTS game_by_season ON game (league_id, season_id);

-- One official's career in the league.
CREATE INDEX IF NOT EXISTS game_official_by_person ON game_official (league_id, person_id);