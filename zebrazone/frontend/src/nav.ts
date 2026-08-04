/**
 * The pages a league has, and which one the URL is asking for.
 *
 * The tab bar is built from this list, so adding a page is one entry here plus
 * the page itself.
 */

export interface Page {
  id: 'games' | 'officials' | 'stats'
  name: string
}

/** Which page is showing: one of the below, or the picker they're chosen from. */
export type View = Page['id'] | 'home'

/** Which page the URL is asking for; anything unrecognised means the homepage. */
export function viewFromHash(): View {
  const asked = location.hash.slice(1)
  return PAGES.some((page) => page.id === asked) ? (asked as Page['id']) : 'home'
}

export const PAGES: Page[] = [
  { id: 'games', name: 'Games' },
  { id: 'officials', name: 'Officials' },
  { id: 'stats', name: 'Stats' },
]
