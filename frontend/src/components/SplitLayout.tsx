import type { ReactNode } from 'react'
import hand from '@/assets/hand-point.jpg'
import { cn } from '@/lib/utils'
import { Brand } from './Brand'
import { Disclaimer } from './Disclaimer'

interface Props {
  /** Content for the calm left-hand panel, below the illustration. */
  aside: ReactNode
  /** Optional navigation shown at the top of the main area. */
  nav?: ReactNode
  children: ReactNode
}

/** The two-column pressure·point layout: calm panel on the left, content on the right. */
export function SplitLayout({ aside, nav, children }: Props) {
  return (
    <div className="relative min-h-screen bg-background font-sans text-foreground">
      <div className="grid min-h-screen lg:grid-cols-[5fr_7fr]">
        <aside
          className={cn(
            'relative flex flex-col justify-between gap-8 bg-calm p-6 sm:p-8 lg:sticky lg:top-0 lg:h-screen lg:overflow-y-auto lg:p-12',
            nav && 'pt-16 sm:pt-20 lg:pt-12', // room for the nav row above the brand on small screens
          )}
        >
          <Brand />
          <div className="animate-rise">
            <img
              src={hand}
              alt="Hand with a gently glowing acupressure point"
              width={1024}
              height={768}
              className="mb-6 hidden w-full max-w-sm rounded-3xl mix-blend-multiply sm:block"
            />
            {aside}
          </div>
          <Disclaimer />
        </aside>
        <main className="p-6 sm:p-8 lg:p-12">
          {/* A row above the brand on small screens, top of the content column on large ones. */}
          {nav && (
            <nav className="absolute right-3 top-3 flex gap-1 sm:right-5 sm:top-5 lg:static lg:mb-8 lg:justify-end lg:gap-2">
              {nav}
            </nav>
          )}
          {children}
        </main>
      </div>
    </div>
  )
}
