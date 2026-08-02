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

  return (
    <main>
      <h1>ZebraZone</h1>

      <div className="controls">
        <label>
          League
          <select value={league} onChange={(event) => setLeague(event.target.value)}>
            {leagues.map((option) => (
              <option key={option.id} value={option.id}>
                {option.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Date
          <input
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
          />
        </label>
      </div>

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
  )
}
