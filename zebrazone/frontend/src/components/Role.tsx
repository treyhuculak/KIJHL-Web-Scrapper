import './Role.css'

/** What each job is called on screen. The API keeps the formal words. */
const SHOWN: Record<string, string> = {
  Referee: 'Referee',
  Linesperson: 'Lines',
  Both: '50/50',
}

const SHADE: Record<string, string> = {
  Referee: 'pill referee',
  Both: 'pill split',
}

/**
 * The job an official worked, as one pill.
 *
 * A referee wears the armband and the lines wear black, which is what those two
 * colours mean everywhere else on the page. Someone who works enough of both is
 * neither, so their pill is neither colour: grey, and it says 50/50.
 */
export function Role({ role }: { role: string }) {
  return <span className={SHADE[role] ?? 'pill'}>{SHOWN[role] ?? role}</span>
}
