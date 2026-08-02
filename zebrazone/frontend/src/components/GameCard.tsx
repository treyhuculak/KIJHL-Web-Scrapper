import { useState } from 'react'
import type { Game, Official, Penalty, Team } from '../api'

/** The team's logo, falling back to its code if the image won't load. */
function TeamCrest({ team }: { team: Team }) {
  const [broken, setBroken] = useState(false)

  if (!team.logo || broken) {
    return <span className="team-code">{team.code}</span>
  }

  // The team's name sits right beside this, so the logo adds nothing to read.
  // The dimensions are given so the row keeps its shape before the image lands.
  return (
    <img
      className="team-logo"
      src={team.logo}
      alt=""
      width={40}
      height={40}
      loading="lazy"
      decoding="async"
      onError={() => setBroken(true)}
    />
  )
}

function TeamRow({ team, lost }: { team: Team; lost: boolean }) {
  return (
    <div className={lost ? 'team lost' : 'team'}>
      <TeamCrest team={team} />
      <span className="team-name">
        <span className="team-city">{team.city}</span>
        <span className="team-nickname">{team.nickname}</span>
      </span>
      <span className="team-goals">{team.goals}</span>
    </div>
  )
}

function PimCell({ label, value, total }: { label: string; value: number; total?: boolean }) {
  return (
    <div className={total ? 'pim total' : 'pim'}>
      <span className="pim-label">{label}</span>
      <span className="pim-value">{value}</span>
    </div>
  )
}

function PenaltyRow({ penalty }: { penalty: Penalty }) {
  return (
    <li className="penalty">
      <span className="penalty-team">{penalty.team_code}</span>
      <span className="penalty-what">
        <span className="penalty-player">{penalty.player}</span>
        <span className="penalty-infraction">{penalty.infraction}</span>
      </span>
      <span className="penalty-when">
        <span className="penalty-minutes">{penalty.minutes} min</span>
        <span className="penalty-time">
          {penalty.period} {penalty.time}
        </span>
      </span>
    </li>
  )
}

/** The crew who worked the game, grouped by role in the order they were listed. */
function Officials({ officials }: { officials: Official[] }) {
  const crews = new Map<string, Official[]>()
  for (const official of officials) {
    const crew = crews.get(official.role) ?? []
    crew.push(official)
    crews.set(official.role, crew)
  }

  return (
    <div className="officials">
      {[...crews].map(([role, crew]) => (
        <div className="crew" key={role}>
          <span className="crew-role">{crew.length === 1 ? role : `${role}s`}</span>
          {crew.map((official) => (
            <span className="crew-name" key={official.name}>
              {official.name}
              {official.number !== null && (
                <span className="crew-number"> ({official.number})</span>
              )}
            </span>
          ))}
        </div>
      ))}
    </div>
  )
}

export function GameCard({ game }: { game: Game }) {
  const { visitor, home, final, notable_penalties: notable } = game

  const pims =
    visitor.pims === null || home.pims === null
      ? null
      : { visitor: visitor.pims, home: home.pims, total: visitor.pims + home.pims }

  return (
    <article className="card">
      <header className="card-header">
        <span className={final ? 'status final' : 'status'}>{game.status}</span>
        {game.attendance !== null && (
          <span className="attendance">{game.attendance.toLocaleString()} fans</span>
        )}
      </header>

      <TeamRow team={visitor} lost={final && visitor.goals < home.goals} />
      <TeamRow team={home} lost={final && home.goals < visitor.goals} />

      {pims && (final || pims.total > 0) && (
        <div className="pims">
          <PimCell label={`${visitor.code} PIM`} value={pims.visitor} />
          <PimCell label="Total" value={pims.total} total />
          <PimCell label={`${home.code} PIM`} value={pims.home} />
        </div>
      )}

      {notable.length > 0 && (
        <details className="notable">
          <summary>Majors &amp; misconducts ({notable.length})</summary>
          <ul className="penalties">
            {/* Fixed list, never reordered, and the feed gives no penalty id. */}
            {notable.map((penalty, index) => (
              <PenaltyRow key={index} penalty={penalty} />
            ))}
          </ul>
        </details>
      )}

      {game.officials.length > 0 && <Officials officials={game.officials} />}

      {game.venue && (
        <footer className="card-footer">
          <span className="venue">{game.venue}</span>
        </footer>
      )}
    </article>
  )
}
