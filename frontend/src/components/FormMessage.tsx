import { cn } from '@/lib/utils'

/** A form-level success or error message, announced politely to screen readers. */
export function FormMessage({ kind, children }: { kind: 'error' | 'success'; children: string }) {
  return (
    <p
      role={kind === 'error' ? 'alert' : 'status'}
      className={cn(
        'rounded-xl p-3 text-sm',
        kind === 'error' ? 'bg-destructive/10 text-destructive' : 'bg-secondary text-secondary-foreground',
      )}
    >
      {children}
    </p>
  )
}
