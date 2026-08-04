import type { League } from '../api'
import { PAGES, type View } from '../nav'
import './Navbar.css'

/**
 * The bar under the masthead: which page you're on, and which league it's about.
 *
 * It sticks to the top, so both stay in reach however far down a page goes. The
 * way back to the picker is the wordmark above rather than a tab in here —
 * there isn't room on a phone for both a tab per page and the league select.
 */
export function Navbar({
  leagues,
  league,
  view,
  onChoose,
}: {
  leagues: League[]
  league: string
  view: View
  onChoose: (id: string) => void
}) {
  return (
    <div className="navbar">
      <nav className="tabs">
        {PAGES.map((page) => (
          <a
            key={page.id}
            className={view === page.id ? 'tab current' : 'tab'}
            href={`#${page.id}`}
          >
            {page.name}
          </a>
        ))}
      </nav>

      <select
        aria-label="League"
        value={league}
        onChange={(event) => onChoose(event.target.value)}
      >
        {leagues.map((option) => (
          // The id doubles as the league's short code, which is all this has
          // room for; the full name sits in the masthead above.
          <option key={option.id} value={option.id}>
            {option.id.toUpperCase()}
          </option>
        ))}
      </select>
    </div>
  )
}
