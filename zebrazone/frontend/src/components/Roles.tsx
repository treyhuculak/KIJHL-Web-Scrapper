import './Roles.css'

/**
 * The job an official worked, as a pill or two.
 *
 * A referee wears the armband, so the referee's pill is the armband colour and
 * the linesperson's is black — the same thing those two colours mean everywhere
 * else on the page. Anyone who worked both jobs enough to count wears both.
 */
export function Roles({ role }: { role: string }) {
  return (
    <span className="roles">
      {role === 'Both' ? (
        <>
          <span className="pill referee">Referee</span>
          <span className="pill">Lines</span>
        </>
      ) : (
        <span className={role === 'Referee' ? 'pill referee' : 'pill'}>
          {role === 'Linesperson' ? 'Lines' : role}
        </span>
      )}
    </span>
  )
}
