import { useEffect, useState } from 'react'
import { getLeagues, type League } from './api'
import { viewFromHash } from './nav'
import { Navbar } from './components/Navbar'
import { Games } from './pages/Games'
import { Home } from './pages/Home'
import './App.css'

/**
 * Where the chosen league is kept. sessionStorage rather than localStorage: the
 * choice holds for this visit — reloads and page changes included — and the app
 * asks again next time it's opened fresh.
 */
const KEPT = 'zebrazone.league'

export default function App() {
  const [leagues, setLeagues] = useState<League[]>([])
  const [league, setLeague] = useState(() => sessionStorage.getItem(KEPT) ?? '')
  const [asked, setAsked] = useState(viewFromHash)
  const [error, setError] = useState<string | null>(null)

  const selected = leagues.find((option) => option.id === league)
  // No league, no pages — a link straight to one lands on the chooser instead.
  const view = league ? asked : 'home'

  /** Switch leagues, staying on whatever page is open. */
  function choose(id: string) {
    setLeague(id)
    sessionStorage.setItem(KEPT, id)
  }

  /** Choosing one from the picker is the way into a league, so open it. */
  function enter(id: string) {
    choose(id)
    location.hash = 'games'
  }

  // Load the league list once. A league we were left pointed at can have been
  // hidden since, so anything not on offer any more sends us back to the chooser.
  useEffect(() => {
    getLeagues()
      .then((found) => {
        setLeagues(found)
        setLeague((current) => {
          if (found.some((option) => option.id === current)) return current
          sessionStorage.removeItem(KEPT)
          return ''
        })
      })
      .catch((problem: Error) => setError(problem.message))
  }, [])

  // Follow the address bar, so the tabs and the back button agree.
  useEffect(() => {
    const follow = () => setAsked(viewFromHash())
    window.addEventListener('hashchange', follow)
    return () => window.removeEventListener('hashchange', follow)
  }, [])

  // Repaint the page in the selected league's armband colour.
  useEffect(() => {
    if (selected) {
      document.documentElement.style.setProperty('--armband', selected.accent)
    }
  }, [selected])

  return (
    <div className="page">
      <header className="masthead">
        <h1 className="wordmark">
          Zebra<span>Zone</span>
        </h1>
        <p className="tagline">{selected ? selected.name : 'Officiating, league by league'}</p>
      </header>

      {/* Nothing to navigate until a league is chosen. */}
      {selected && (
        <Navbar leagues={leagues} league={league} view={view} onChoose={choose} />
      )}

      <main>
        {error && <p className="message error">{error}</p>}

        {view === 'home' && (
          <Home leagues={leagues} chosen={selected} onChoose={enter} />
        )}
        {view === 'games' && <Games league={league} />}
        {view === 'officials' && <p className="message">Coming next.</p>}
      </main>

      <footer className="colophon">
        Making hockey officiating data accessible
      </footer>
    </div>
  )
}
