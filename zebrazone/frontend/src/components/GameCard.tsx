import type { Game, Team } from '../api'

function TeamRow({ team, won }: { team: Team; won: boolean }) {
  return (
    <div className={won ? 'team team-won' : 'team'}>
      <span className="team-code">{team.code}</span>
      <span className="team-name">
        {team.city} {team.nickname}
      </span>
      <span className="team-goals">{team.goals}</span>
    </div>
  )
}

export function GameCard({ game }: { game: Game }) {
  const final = game.status === 'Final'

  return (
    <article className="card">
      <header className="card-header">
        <span className="status">{game.status}</span>
        {game.start_time && <span>{game.start_time.slice(0, 5)}</span>}
      </header>

      <TeamRow team={game.visitor} won={final && game.visitor.goals > game.home.goals} />
      <TeamRow team={game.home} won={final && game.home.goals > game.visitor.goals} />

      <footer className="card-footer">
        <span>{game.venue}</span>
        {game.attendance !== null && <span>{game.attendance.toLocaleString()} fans</span>}
      </footer>
    </article>
  )
}
