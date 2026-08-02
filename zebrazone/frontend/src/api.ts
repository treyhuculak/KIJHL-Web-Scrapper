/** Everything the app knows about the backend. */

export interface League {
  id: string
  name: string
  /** The league's armband colour, used to theme the page. */
  accent: string
}

export interface Team {
  code: string
  city: string
  nickname: string
  goals: number
  pims: number
  logo: string
}

/** A penalty worth calling out on its own — a major or a misconduct. */
export interface Penalty {
  team_code: string
  player: string
  infraction: string
  minutes: number
  period: string
  time: string
}

export interface Game {
  id: string
  date: string
  status: string
  /** Whether the game has been played — true for 'Final', 'Final OT', 'Final SO'. */
  final: boolean
  venue: string
  start_time: string | null
  attendance: number | null
  home: Team
  visitor: Team
  notable_penalties: Penalty[]
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `Request failed (${response.status})`)
  }
  return response.json()
}

export function getLeagues(): Promise<League[]> {
  return get<League[]>('/api/leagues')
}

export function getGames(league: string, date: string): Promise<Game[]> {
  return get<Game[]>(`/api/games?league=${league}&date=${date}`)
}
