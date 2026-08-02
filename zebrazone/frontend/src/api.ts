/** Everything the app knows about the backend. */

export interface League {
  id: string
  name: string
}

export interface Team {
  code: string
  city: string
  nickname: string
  goals: number
}

export interface Game {
  id: string
  date: string
  status: string
  venue: string
  start_time: string | null
  attendance: number | null
  home: Team
  visitor: Team
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
