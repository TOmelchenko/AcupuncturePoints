import type { ReactNode } from 'react'
import { SplitLayout } from '@/components/SplitLayout'

/** Shared frame for the sign-in, registration and password pages. */
export function AuthLayout({ title, intro, about, children }: { title: string; intro: string; about?: ReactNode; children: ReactNode }) {
  return (
    <SplitLayout
      aside={
        <>
          <h1 className="font-display text-4xl font-medium leading-tight lg:text-5xl">{title}</h1>
          <p className="mt-3 text-muted-foreground">{intro}</p>
          {about && (
            <section aria-label="About this app" className="mt-6 rounded-2xl bg-card p-4 text-sm text-muted-foreground shadow-soft">
              <p className="font-medium uppercase tracking-widest text-primary">About</p>
              <p className="mt-1">{about}</p>
            </section>
          )}
        </>
      }
    >
      <div className="mx-auto w-full max-w-md rounded-3xl border border-border bg-card p-6 shadow-soft sm:p-8 lg:mt-16">
        {children}
      </div>
    </SplitLayout>
  )
}
