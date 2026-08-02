import { useEffect, useState } from 'react'
import { getGames, getLeagues, type Game, type League } from './api'
import { GameCard } from './components/GameCard'
import './App.css'

/** Today in the user's own timezone, as YYYY-MM-DD. */
function today(): string {
  return new Date().toLocaleDateString('en-CA')
}

export default function App() {
  const [leagues, setLeagues] = useState<League[]>([])
  const [league, setLeague] = useState('')
  const [date, setDate] = useState(today())

  const [games, setGames] = useState<Game[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selected = leagues.find((option) => option.id === league)

  // Load the league list once, and start on the first one.
  useEffect(() => {
    getLeagues()
      .then((found) => {
        setLeagues(found)
        setLeague(found[0]?.id ?? '')
      })
      .catch((problem: Error) => setError(problem.message))
  }, [])

  // Reload games whenever the league or the date changes.
  useEffect(() => {
    if (!league) return

    let current = true
    setLoading(true)
    setError(null)

    getGames(league, date)
      .then((found) => current && setGames(found))
      .catch((problem: Error) => current && setError(problem.message))
      .finally(() => current && setLoading(false))

    return () => {
      current = false
    }
  }, [league, date])

  // Repaint the page in the selected league's armband colour.
  useEffect(() => {
    if (selected) {
      document.documentElement.style.setProperty('--armband', selected.accent)
    }
  }, [selected])

  return (
    <div className="page">
      <header className="masthead">
        <h1 className="wordmark">
          Zebra<span>Zone</span>
        </h1>
        <p className="tagline">{selected?.name}</p>
      </header>

      <div className="controls">
        <label>
          <span className="field-label">League</span>
          <select value={league} onChange={(event) => setLeague(event.target.value)}>
            {leagues.map((option) => (
              // The id doubles as the league's short code, which is all the
              // picker has room for; the full name sits in the masthead.
              <option key={option.id} value={option.id}>
                {option.id.toUpperCase()}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className="field-label">Date</span>
          <input
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
          />
        </label>
      </div>

      <main>
        {error && <p className="message error">{error}</p>}
        {loading && <p className="message">Loading games…</p>}
        {!loading && !error && games.length === 0 && (
          <p className="message">No games on this date.</p>
        )}

        <div className="games">
          {games.map((game) => (
            <GameCard key={game.id} game={game} />
          ))}
        </div>
      </main>

      <footer className="colophon">
        Making hockey officiating data accessible
      </footer>
    </div>
  )
}
