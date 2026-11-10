import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router'
import { AppNav } from '@/components/AppNav'
import { Disclaimer } from '@/components/Disclaimer'
import { FormMessage } from '@/components/FormMessage'
import { SplitLayout } from '@/components/SplitLayout'
import { Button } from '@/components/ui/button'
import { formatDate, OUTCOME_LABEL } from '@/history/format'
import { api, ApiError } from '@/lib/api'
import type { HistoryDetail } from '@/lib/types'
import { RecommendationList } from '@/recommendations/RecommendationList'

const CARD = 'rounded-3xl border border-border bg-card p-6 shadow-soft sm:p-8'

function Detail({ detail }: { detail: HistoryDetail }) {
  return (
    <section aria-labelledby="detail-heading" className="animate-rise">
      <p className="text-sm font-medium uppercase tracking-widest text-primary">
        {OUTCOME_LABEL[detail.outcome]} · <time dateTime={detail.created_at}>{formatDate(detail.created_at)}</time>
      </p>
      <h2 id="detail-heading" className="mt-2 font-display text-3xl font-medium">
        For “{detail.symptom}”
      </h2>
      {detail.clarification_question && (
        <dl className="mt-4 space-y-1 text-sm">
          <div>
            <dt className="inline font-medium">We asked: </dt>
            <dd className="inline text-muted-foreground">{detail.clarification_question}</dd>
          </div>
          {detail.clarification_answer && (
            <div>
              <dt className="inline font-medium">You answered: </dt>
              <dd className="inline text-muted-foreground">{detail.clarification_answer}</dd>
            </div>
          )}
        </dl>
      )}
      {detail.outcome === 'recommended' && (
        <>
          <RecommendationList attemptId={detail.attempt_id} points={detail.points} />
          <Disclaimer className="mt-8" />
        </>
      )}
      {detail.outcome === 'clarification_needed' && (
        <p className={`${CARD} mt-6 text-muted-foreground`}>
          This request stopped at the clarifying question, so no points were recommended.
        </p>
      )}
      {detail.outcome === 'no_match' && (
        <p className={`${CARD} mt-6 text-muted-foreground`}>
          We couldn't find suitable acupressure points for this description.
        </p>
      )}
    </section>
  )
}

export function HistoryDetailPage() {
  const { attemptId = '' } = useParams()
  const query = useQuery({
    queryKey: ['history', 'detail', attemptId],
    queryFn: () => api.historyItem(attemptId),
  })

  let content
  if (query.isPending) {
    content = (
      <div role="status" aria-label="Loading recommendation" className="space-y-5">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-40 animate-pulse rounded-3xl bg-card shadow-soft" />
        ))}
      </div>
    )
  } else if (query.isError) {
    const notFound = query.error instanceof ApiError && query.error.status === 404
    content = (
      <div className={`${CARD} space-y-4`}>
        <FormMessage kind="error">{query.error.message}</FormMessage>
        {!notFound && (
          <Button className="rounded-full px-6" onClick={() => query.refetch()}>
            Try again
          </Button>
        )}
      </div>
    )
  } else {
    content = <Detail detail={query.data} />
  }

  return (
    <SplitLayout
      nav={<AppNav />}
      aside={
        <>
          <h1 className="font-display text-4xl font-medium leading-tight lg:text-5xl">Your history</h1>
          <p className="mt-3 text-muted-foreground">
            Tried a point since? Rate it below — a new rating replaces the earlier one.
          </p>
        </>
      }
    >
      <Link
        to="/history"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden="true" /> All history
      </Link>
      {content}
    </SplitLayout>
  )
}
