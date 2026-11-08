import type { Session } from '@supabase/supabase-js'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MemoryRouter } from 'react-router'
import { AuthContext } from '@/auth/context'

export const SESSION = {
  access_token: 'test-token',
  user: { id: 'user-1', email: 'user@example.test' },
} as unknown as Session

interface Options {
  route?: string
  session?: Session | null
  loading?: boolean
}

/** Render with the app's providers: auth state, TanStack Query and an in-memory router. */
export function renderWithProviders(ui: ReactElement, options: Options = {}) {
  const { route = '/', session = SESSION, loading = false } = options
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={{ session, loading }}>
        <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
      </AuthContext.Provider>
    </QueryClientProvider>,
  )
}
