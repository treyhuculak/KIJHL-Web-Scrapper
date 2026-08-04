/** Everything the app knows about the backend. */

export interface League {
  id: string
  name: string
  /** The league's armband colour, used to theme the page. */
  accent: string
  /** 'Major junior', 'Junior A' or 'Junior B' — the picker groups by it. The
   *  backend sends the leagues in tier order, so grouping keeps that order. */
  tier: string
}

export interface Team {
  code: string
  city: string
  nickname: string
  goals: number
  /** Penalty minutes, or null when the league can't serve game summaries. */
  pims: number | null
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

/** One of the four officials who worked the game. */
export interface Official {
  /** The feed's own id for them, scoped to the league. */
  person_id: string
  name: string
  /** 'Referee' or 'Linesperson'. */
  role: string
  /** Jersey number, or null in leagues that don't give officials one. */
  number: number | null
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
  officials: Official[]
}

/** A season a league has played. Playoffs arrive as one of these too. */
export interface Season {
  id: string
  name: string
  playoff: boolean
  starts_on: string | null
}

/** One official's season, counted up out of the games they worked. */
export interface OfficialSeason {
  person_id: string
  name: string
  number: number | null
  /** 'Referee', 'Linesperson', or 'Both' — the last only for officials who
   *  spent a real part of the season on each, not for one night filling in. */
  role: string
  games: number
  pims: number
  pims_per_game: number
  /** Majors and match penalties called in their games, fighting aside. */
  majors: number
  fights: number
}

/**
 * A season's standouts.
 *
 * Every figure counts what happened in the games an official worked, not what
 * they called: the feed names the crew and the penalties, never which of the
 * four blew the whistle.
 */

/** One official on one leaderboard. */
export interface Leader {
  person_id: string
  name: string
  role: string
  games: number
  /** However many of the thing this board counts. */
  total: number
  per_game: number
}

/** Two officials who work the same job, and how often they're put together. */
export interface Partnership {
  names: string[]
  games: number
  pims_per_game: number
}

/** A game, and the crew who had it. */
export interface CrewedGame {
  game_id: string
  played_on: string
  home_code: string
  visitor_code: string
  home_goals: number | null
  visitor_goals: number | null
  pims: number
  majors: number
  fights: number
  crew: Official[]
}

export interface SeasonStats {
  fights: Leader[]
  majors: Leader[]
  wildest: CrewedGame[]
  referee_pairs: Partnership[]
  line_pairs: Partnership[]
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

/** The seasons we hold games for, the one being played first. */
export function getSeasons(league: string): Promise<Season[]> {
  return get<Season[]>(`/api/seasons?league=${league}`)
}

export function getOfficials(league: string, season: string): Promise<OfficialSeason[]> {
  return get<OfficialSeason[]>(`/api/officials?league=${league}&season=${season}`)
}

export function getStats(league: string, season: string): Promise<SeasonStats> {
  return get<SeasonStats>(`/api/stats?league=${league}&season=${season}`)
}
