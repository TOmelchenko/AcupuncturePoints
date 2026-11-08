import { useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { supabase } from '@/lib/supabase'

export function SignOutButton() {
  const queryClient = useQueryClient()
  return (
    <Button
      variant="ghost"
      className="rounded-full"
      onClick={async () => {
        await supabase.auth.signOut()
        queryClient.clear() // drop any cached data from the previous user
      }}
    >
      Sign out
    </Button>
  )
}
