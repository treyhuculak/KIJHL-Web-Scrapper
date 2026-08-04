import { useEffect, useState } from 'react'
import {
  getStats,
  type CrewedGame,
  type Leader,
  type Official,
  type Partnership,
  type SeasonStats,
} from '../api'
import { Roles } from '../components/Roles'
import { useSeasons } from '../seasons'
import './Stats.css'

const NOTHING: SeasonStats = {
  fights: [],
  majors: [],
  wildest: [],
  referee_pairs: [],
  line_pairs: [],
}

/** A date the way a schedule writes it, and in the reader's own timezone: a
 *  bare YYYY-MM-DD is read as UTC, which is yesterday west of Greenwich. */
function when(played: string): string {
  return new Date(`${played}T00:00`).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })
}

function count(many: number, thing: string): string {
  return `${many} ${thing}${many === 1 ? '' : 's'}`
}

function Board({
  title,
  note,
  wide,
  children,
}: {
  title: string
  note: string
  wide?: boolean
  children: React.ReactNode
}) {
  return (
    <section className={wide ? 'board wide' : 'board'}>
      <h2>{title}</h2>
      <p className="board-note">{note}</p>
      {children}
    </section>
  )
}

/** A row's figures: the count that ranks it, and the rate underneath. */
function Figure({ total, unit, rate }: { total: number; unit: string; rate: string }) {
  return (
    <span className="rank-figure">
      <span className="rank-total">
        {total} <span className="rank-unit">{unit}</span>
      </span>
      <span className="rank-rate">{rate}</span>
    </span>
  )
}

function People({ rows, unit }: { rows: Leader[]; unit: string }) {
  return (
    <ol className="rank">
      {rows.map((one) => (
        <li key={one.person_id}>
          <span className="rank-who">
            <span className="rank-name">{one.name}</span>
            <Roles role={one.role} />
          </span>
          <Figure total={one.total} unit={unit} rate={`${one.per_game.toFixed(2)} a game`} />
        </li>
      ))}
    </ol>
  )
}

function Pairs({ rows }: { rows: Partnership[] }) {
  return (
    <ol className="rank">
      {rows.map((pair) => (
        <li key={pair.names.join()}>
          <span className="rank-who">
            <span className="rank-name">{pair.names.join(' & ')}</span>
          </span>
          <Figure
            total={pair.games}
            unit="together"
            rate={`${pair.pims_per_game.toFixed(1)} pim a game`}
          />
        </li>
      ))}
    </ol>
  )
}

/** The crew of one game, refs above lines, as the sheet lists them. */
function Crew({ crew }: { crew: Official[] }) {
  const jobs = [
    { label: 'Ref', worked: crew.filter((one) => one.role === 'Referee') },
    { label: 'Lines', worked: crew.filter((one) => one.role === 'Linesperson') },
  ]

  return (
    <div className="wild-crew">
      {jobs
        .filter((job) => job.worked.length > 0)
        .map((job) => (
          <p key={job.label}>
            <span className={job.label === 'Ref' ? 'crew-job referee' : 'crew-job'}>
              {job.label}
            </span>
            {job.worked.map((one) => one.name).join(' · ')}
          </p>
        ))}
    </div>
  )
}

function Wildest({ games }: { games: CrewedGame[] }) {
  return (
    <ol className="wild">
      {games.map((game) => (
        <li key={game.game_id}>
          <div className="wild-line">
            <span className="wild-when">{when(game.played_on)}</span>
            <span className="wild-score">
              {game.visitor_code} {game.visitor_goals} @ {game.home_code} {game.home_goals}
            </span>
            <span className="wild-pims">
              {game.pims} <span className="rank-unit">pim</span>
            </span>
          </div>

          <p className="wild-tally">
            {[
              game.fights > 0 && count(game.fights, 'fight'),
              game.majors > 0 && count(game.majors, 'major'),
            ]
              .filter(Boolean)
              .join(' · ') || 'Minors all night'}
          </p>

          <Crew crew={game.crew} />
        </li>
      ))}
    </ol>
  )
}

/**
 * What stood out about a season: the fights, the majors, the nights nobody
 * forgets, and who gets put together.
 *
 * Everything here counts what happened in the games an official worked, which
 * is not the same as what they called — the feed names the crew and it names
 * the penalties, but never which of the four blew the whistle. The page says so
 * at the bottom rather than dressing the numbers up as something they aren't.
 */
export function Stats({ league }: { league: string }) {
  const { seasons, season, choose, listed, error: seasonsError } = useSeasons(league)
  const [stats, setStats] = useState<SeasonStats>(NOTHING)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!season) {
      setStats(NOTHING)
      return
    }

    let current = true
    setLoading(true)
    setError(null)

    getStats(league, season)
      .then((found) => current && setStats(found))
      .catch((problem: Error) => current && setError(problem.message))
      .finally(() => current && setLoading(false))

    return () => {
      current = false
    }
  }, [league, season])

  const trouble = seasonsError ?? error
  const anything =
    stats.fights.length > 0 ||
    stats.majors.length > 0 ||
    stats.wildest.length > 0 ||
    stats.referee_pairs.length > 0 ||
    stats.line_pairs.length > 0

  return (
    <>
      {seasons.length > 0 && (
        <div className="filters">
          <select
            aria-label="Season"
            value={season}
            onChange={(event) => choose(event.target.value)}
          >
            {seasons.map((one) => (
              <option key={one.id} value={one.id}>
                {one.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {trouble && <p className="message error">{trouble}</p>}
      {!listed && !trouble && <p className="message">Loading seasons…</p>}
      {listed && !trouble && seasons.length === 0 && (
        <p className="message">No seasons have been stored for this league yet.</p>
      )}
      {loading && <p className="message">Reading the season…</p>}
      {!loading && !trouble && season && !anything && (
        <p className="message">Nothing was recorded for this season.</p>
      )}

      {!loading && anything && (
        <>
          <div className="boards">
            <Board
              title="Majors called"
              note="Referees, by the majors called in their games"
            >
              <People rows={stats.majors} unit="majors" />
            </Board>

            <Board
              title="Fights broken up"
              note="Lines, by the fights they have broken up in their games"
            >
              <People rows={stats.fights} unit="fights" />
            </Board>

            <Board
              title="Wildest games"
              note="The season's heaviest nights, and who had them"
              wide
            >
              <Wildest games={stats.wildest} />
            </Board>

            <Board
              title="Referee partnerships"
              note="The referee pairings put together most often in the season"
            >
              <Pairs rows={stats.referee_pairs} />
            </Board>

            <Board
              title="Line partnerships"
              note="The lines pairings put together most often in the season"
            >
              <Pairs rows={stats.line_pairs} />
            </Board>
          </div>

          <p className="footnote">
            Counted from the games each official worked. The feed records the crew and it
            records the penalties, but never which of the four made the call — so these are
            the officials who saw the most of something, not the ones who called it.
          </p>
        </>
      )}
    </>
  )
}
