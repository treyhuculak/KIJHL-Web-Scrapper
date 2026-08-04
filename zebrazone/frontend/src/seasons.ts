import { useEffect, useState } from 'react'
import { getSeasons, type Season } from './api'

/**
 * The seasons a league has, and which of them is being looked at.
 *
 * Both pages built on stored history need this, and need it to answer the same
 * way: open on the season being played, and never offer a season the chosen
 * league doesn't have.
 */
export function useSeasons(league: string) {
  // The seasons are kept with the league they were fetched for, so a league
  // change can't leave last league's seasons on screen for a render.
  const [loaded, setLoaded] = useState<{ league: string; seasons: Season[] }>({
    league: '',
    seasons: [],
  })
  const [picked, setPicked] = useState('')
  const [error, setError] = useState<string | null>(null)

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

  const listed = loaded.league === league
  const seasons = listed ? loaded.seasons : []

  return {
    seasons,
    // The season being played, until the reader asks for another. Derived
    // rather than stored, so it's never a season this league doesn't have.
    season: seasons.some((one) => one.id === picked) ? picked : (seasons[0]?.id ?? ''),
    choose: setPicked,
    /** Whether the list on hand is this league's, rather than one on its way. */
    listed,
    error,
  }
}
