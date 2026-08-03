import type { CSSProperties } from 'react'
import type { League } from '../api'
import './Home.css'

/**
 * Every league logo in assets/leagues, keyed by the league id its filename gives.
 *
 * Adding one is dropping in a file named after the league — any image format,
 * since the extension is only used to strip it back off again. Vite resolves the
 * lot at build time, so a league with no logo is known here rather than found out
 * by a request that 404s.
 */
const LOGOS: Record<string, string> = Object.fromEntries(
  Object.entries(
    import.meta.glob<string>('../assets/leagues/*', {
      eager: true,
      query: '?url',
      import: 'default',
    }),
  ).map(([path, url]) => [path.split('/').pop()!.replace(/\.\w+$/, ''), url]),
)

/** The league's logo, or an empty ring so the cards line up without one. */
function LeagueCrest({ league }: { league: League }) {
  const logo = LOGOS[league.id]

  if (!logo) {
    return <span className="tile-logo empty" aria-hidden="true" />
  }

  // The league's name and code sit right beside this, so the logo adds nothing
  // to read. The dimensions are given so the card keeps its shape before the
  // image lands.
  return <img className="tile-logo" src={logo} alt="" width={48} height={48} />
}

/** The leagues under their tier, keeping the order the backend sent them in. */
function byTier(leagues: League[]): Map<string, League[]> {
  const tiers = new Map<string, League[]>()
  for (const league of leagues) {
    const tier = tiers.get(league.tier) ?? []
    tier.push(league)
    tiers.set(league.tier, tier)
  }
  return tiers
}

/**
 * The homepage, and the app's front door: pick a league, and every page you open
 * afterwards is that league's.
 *
 * The picker stays on screen after a choice is made — it's what this page is for,
 * and the league's pages are one tap away in the bar above.
 */
export function Home({
  leagues,
  chosen,
  onChoose,
}: {
  leagues: League[]
  chosen: League | undefined
  onChoose: (id: string) => void
}) {
  return (
    <div className="home">
      <h2 className="home-title">Pick a league</h2>

      {leagues.length === 0 && <p className="message">Loading leagues…</p>}

      {[...byTier(leagues)].map(([tier, group]) => (
        <section className="tier" key={tier}>
          <h3 className="tier-name">{tier}</h3>
          <div className="tiles">
            {group.map((league) => (
              <button
                key={league.id}
                type="button"
                className={league.id === chosen?.id ? 'card tile chosen' : 'card tile'}
                aria-pressed={league.id === chosen?.id}
                // Each card wears its own league's armband colour, so the choice
                // shows what the app is about to look like. Inline, because it's
                // the league's own and beats anything a stylesheet says.
                style={
                  {
                    '--edge': league.accent,
                    '--edge-hover': league.accent,
                  } as CSSProperties
                }
                onClick={() => onChoose(league.id)}
              >
                <LeagueCrest league={league} />
                <span className="tile-name">{league.name}</span>
              </button>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
