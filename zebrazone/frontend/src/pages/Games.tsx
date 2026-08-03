import { useEffect, useState } from 'react'
import { getGames, type Game } from '../api'
import { GameCard } from '../components/GameCard'

/** Today in the user's own timezone, as YYYY-MM-DD. */
function today(): string {
  return new Date().toLocaleDateString('en-CA')
}

/** Every game the chosen league played on one day. */
export function Games({ league }: { league: string }) {
  const [date, setDate] = useState(today())
  const [games, setGames] = useState<Game[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Reload games whenever the league or the date changes.
  useEffect(() => {
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
    <>
      <div className="filters">
        <label>
          <span>Date</span>
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
    </>
  )
}
