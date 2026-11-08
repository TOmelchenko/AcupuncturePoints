import { cn } from '@/lib/utils'

export const DISCLAIMER =
  'For general wellness information only — not a diagnosis, emergency service or substitute ' +
  'for professional medical care. Stop if a point causes pain or discomfort, and seek ' +
  'professional advice if you are concerned about a symptom.'

export function Disclaimer({ className }: { className?: string }) {
  return <p className={cn('text-xs text-muted-foreground', className)}>{DISCLAIMER}</p>
}
