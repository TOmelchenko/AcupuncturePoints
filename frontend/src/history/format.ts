import type { HistoryOutcome } from '@/lib/types'

const DATE = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

export const formatDate = (iso: string) => DATE.format(new Date(iso))

export const OUTCOME_LABEL: Record<HistoryOutcome, string> = {
  recommended: 'Three points',
  clarification_needed: 'Needed more detail',
  no_match: 'No match',
}
