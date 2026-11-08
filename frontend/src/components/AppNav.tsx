import { Link, useLocation } from 'react-router'
import { SignOutButton } from '@/auth/SignOutButton'
import { Button } from '@/components/ui/button'

/** Navigation for signed-in pages. */
export function AppNav() {
  const onAccount = useLocation().pathname === '/account'
  return (
    <>
      <Button asChild variant="ghost" className="rounded-full">
        {onAccount ? <Link to="/">Find points</Link> : <Link to="/account">Account</Link>}
      </Button>
      <SignOutButton />
    </>
  )
}
