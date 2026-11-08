import type { ReactNode } from 'react'
import { SplitLayout } from '@/components/SplitLayout'

/** Shared frame for the sign-in, registration and password pages. */
export function AuthLayout({ title, intro, children }: { title: string; intro: string; children: ReactNode }) {
  return (
    <SplitLayout
      aside={
        <>
          <h1 className="font-display text-4xl font-medium leading-tight lg:text-5xl">{title}</h1>
          <p className="mt-3 text-muted-foreground">{intro}</p>
        </>
      }
    >
      <div className="mx-auto w-full max-w-md rounded-3xl border border-border bg-card p-6 shadow-soft sm:p-8 lg:mt-16">
        {children}
      </div>
    </SplitLayout>
  )
}
