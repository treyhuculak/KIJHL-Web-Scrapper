import { useEffect, useMemo, useState } from 'react'
import { getOfficials, getSeasons, type OfficialSeason, type Season } from '../api'
import './Officials.css'

/**
 * The countable columns, in the order they're shown.
 *
 * Two names each: the word, and the short form a phone has room for. The word
 * is what the column is called either way — it's the heading's aria-label — so
 * nothing is lost by narrowing it, only shortened.
 */
const FIGURES = [
  { key: 'games', label: 'Games', short: 'GP' },
  { key: 'pims_per_game', label: 'PIM/G', short: 'PIM/G' },
  { key: 'pims', label: 'PIM', short: 'PIM' },
  { key: 'majors', label: 'Majors', short: 'MAJ' },
  { key: 'fights', label: 'Fights', short: 'FGT' },
] as const

type Figure = (typeof FIGURES)[number]['key']

/** Whole numbers everywhere but the average, which is worth its decimal. */
function shown(official: OfficialSeason, figure: Figure): string {
  const value = official[figure]
  return figure === 'pims_per_game' ? value.toFixed(1) : String(value)
}

/**
 * The job an official worked, beside their name.
 *
 * A referee wears the armband, so the referee's pill is the armband colour and
 * the linesperson's is black — the same thing the page's palette already means.
 * Anyone who worked both jobs enough to count wears both.
 */
function Role({ role }: { role: string }) {
  if (role === 'Both') {
    return (
      <>
        <span className="pill referee">Referee</span>
        <span className="pill">Lines</span>
      </>
    )
  }

  return (
    <span className={role === 'Referee' ? 'pill referee' : 'pill'}>
      {role === 'Linesperson' ? 'Lines' : role}
    </span>
  )
}

/**
 * Every official who worked one season of the chosen league.
 *
 * One season at a time, never a career or a span of years: playoffs are their
 * own season here, as they are upstream, so nothing is silently averaged
 * together and every figure on the page is a figure from the same competition.
 */
export function Officials({ league }: { league: string }) {
  // The seasons are kept with the league they were fetched for, so a league
  // change can't leave last league's seasons on screen for a render.
  const [loaded, setLoaded] = useState<{ league: string; seasons: Season[] }>({
    league: '',
    seasons: [],
  })
  const [picked, setPicked] = useState('')
  const [officials, setOfficials] = useState<OfficialSeason[]>([])
  const [sort, setSort] = useState<{ by: Figure; descending: boolean }>({
    by: 'games',
    descending: true,
  })
  const [search, setSearch] = useState('')
  const [role, setRole] = useState('')
  const [fewest, setFewest] = useState('')
  const [showing, setShowing] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const listed = loaded.league === league
  const seasons = listed ? loaded.seasons : []
  // The season being played, until the reader asks for another. Derived rather
  // than stored, so it's never a season this league doesn't have.
  const season = seasons.some((one) => one.id === picked) ? picked : (seasons[0]?.id ?? '')

  useEffect(() => {
    let current = true
    setError(null)

    getSeasons(league)
      .then((found) => current && setLoaded({ league, seasons: found }))
      .catch((problem: Error) => current && setError(problem.message))

    return () => {
      current = false
    }
  }, [league])

  useEffect(() => {
    if (!season) {
      setOfficials([])
      return
    }

    let current = true
    setLoading(true)
    setError(null)

    getOfficials(league, season)
      .then((found) => current && setOfficials(found))
      .catch((problem: Error) => current && setError(problem.message))
      .finally(() => current && setLoading(false))

    return () => {
      current = false
    }
  }, [league, season])

  const shortlist = useMemo(() => {
    const wanted = search.trim().toLowerCase()
    const floor = Number(fewest) || 0

    return officials.filter(
      (one) =>
        (!wanted || one.name.toLowerCase().includes(wanted)) &&
        (!role || one.role === role || one.role === 'Both') &&
        one.games >= floor,
    )
  }, [officials, search, role, fewest])

  // Ties break by name, so a column of equal numbers still reads alphabetically
  // and the order doesn't shuffle when the same table is sorted twice.
  const rows = useMemo(() => {
    const gap = (a: OfficialSeason, b: OfficialSeason) => a[sort.by] - b[sort.by]
    return [...shortlist].sort(
      (a, b) => (sort.descending ? -gap(a, b) : gap(a, b)) || a.name.localeCompare(b.name),
    )
  }, [shortlist, sort])

  /** Sort by a column: most first, or least first if it's already the one. */
  function reorder(by: Figure) {
    setSort((current) =>
      current.by === by ? { by, descending: !current.descending } : { by, descending: true },
    )
  }

  return (
    <>
      {seasons.length > 0 && (
        <div className="filters roster-filters">
          <select
            aria-label="Season"
            value={season}
            onChange={(event) => setPicked(event.target.value)}
          >
            {seasons.map((one) => (
              <option key={one.id} value={one.id}>
                {one.name}
              </option>
            ))}
          </select>

          {/* Phones only; a wider screen has the room to leave them all out. */}
          <button
            type="button"
            className="more-toggle"
            aria-expanded={showing}
            aria-controls="officials-filters"
            onClick={() => setShowing(!showing)}
          >
            Filter
            <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
              <path
                d="M2 4h12M4 8h8M6.5 12h3"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>

          <div id="officials-filters" className={showing ? 'more open' : 'more'}>
            <input
              className="find"
              type="search"
              aria-label="Search name"
              placeholder="Search name"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />

            <select
              className="pick"
              aria-label="Role"
              value={role}
              onChange={(event) => setRole(event.target.value)}
            >
              <option value="">All roles</option>
              <option value="Referee">Referees</option>
              <option value="Linesperson">Lines</option>
            </select>

            <input
              className="count"
              type="number"
              min={0}
              aria-label="Minimum games"
              placeholder="Min GP"
              value={fewest}
              onChange={(event) => setFewest(event.target.value)}
            />
          </div>
        </div>
      )}

      {error && <p className="message error">{error}</p>}
      {!listed && !error && <p className="message">Loading seasons…</p>}
      {listed && !error && seasons.length === 0 && (
        <p className="message">No seasons have been stored for this league yet.</p>
      )}
      {loading && <p className="message">Loading officials…</p>}
      {!loading && !error && season && officials.length === 0 && (
        <p className="message">No officials worked this season.</p>
      )}
      {officials.length > 0 && rows.length === 0 && (
        <p className="message">
          None of this season&rsquo;s {officials.length} officials match those filters.
        </p>
      )}

      {rows.length > 0 && (
        <div className="roster-scroll">
          <table className="roster">
            <thead>
              <tr>
                <th scope="col" className="who">
                  Official
                </th>
                {FIGURES.map((figure) => (
                  <th
                    key={figure.key}
                    scope="col"
                    className="figure"
                    aria-sort={
                      sort.by === figure.key
                        ? sort.descending
                          ? 'descending'
                          : 'ascending'
                        : 'none'
                    }
                  >
                    <button
                      type="button"
                      className="sort"
                      aria-label={figure.label}
                      onClick={() => reorder(figure.key)}
                    >
                      <span className="long">{figure.label}</span>
                      <span className="short">{figure.short}</span>
                      {sort.by === figure.key && (
                        <span className="arrow" aria-hidden="true">
                          {sort.descending ? '▾' : '▴'}
                        </span>
                      )}
                    </button>
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {rows.map((official) => (
                <tr key={official.person_id}>
                  <th scope="row" className="who">
                    {/* The cell can't be the flex row itself without giving up
                        being a table cell, so the row is inside it. */}
                    <div className="who-line">
                      <span className="who-name">
                        {official.name}
                        {official.number !== null && (
                          <span className="who-number"> #{official.number}</span>
                        )}
                      </span>
                      <span className="roles">
                        <Role role={official.role} />
                      </span>
                    </div>
                  </th>
                  {FIGURES.map((figure) => (
                    <td key={figure.key} className="figure">
                      {shown(official, figure.key)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
