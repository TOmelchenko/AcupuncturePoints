import { Link, useLocation } from 'react-router'
import { SignOutButton } from '@/auth/SignOutButton'
import { Button } from '@/components/ui/button'

const LINKS = [
  { to: '/', label: 'Find points' },
  { to: '/history', label: 'History' },
  { to: '/account', label: 'Account' },
]

/** Navigation for signed-in pages: links to the other pages, then sign out. */
export function AppNav() {
  const { pathname } = useLocation()
  const section = '/' + pathname.split('/')[1]
  return (
    <>
      {LINKS.filter((link) => link.to !== section).map((link) => (
        <Button key={link.to} asChild variant="ghost" className="rounded-full px-3 sm:px-4">
          <Link to={link.to}>{link.label}</Link>
        </Button>
      ))}
      <SignOutButton />
    </>
  )
}
