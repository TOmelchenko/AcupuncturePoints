import { useInfiniteQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { AppNav } from '@/components/AppNav'
import { FormMessage } from '@/components/FormMessage'
import { SplitLayout } from '@/components/SplitLayout'
import { Button } from '@/components/ui/button'
import { formatDate, OUTCOME_LABEL } from '@/history/format'
import { api } from '@/lib/api'
import type { HistoryItem } from '@/lib/types'

const PAGE_SIZE = 20
const CARD = 'rounded-3xl border border-border bg-card p-6 shadow-soft sm:p-8'

function HistoryRow({ item }: { item: HistoryItem }) {
  return (
    <li>
      <Link
        to={`/history/${item.attempt_id}`}
        className="block rounded-3xl border border-border bg-card p-5 shadow-soft transition-colors hover:border-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:p-6"
      >
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
          <time dateTime={item.created_at} className="text-muted-foreground">
            {formatDate(item.created_at)}
          </time>
          <span className="rounded-full bg-secondary px-3 py-1 font-medium text-secondary-foreground">
            {OUTCOME_LABEL[item.outcome]}
          </span>
        </div>
        <p className="mt-2 line-clamp-2 font-display text-lg font-medium">“{item.symptom}”</p>
        {item.points.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-2 text-xs" aria-label="Recommended points">
            {item.points.map((p) => (
              <li key={p.point_id} className="rounded-full border border-border px-3 py-1">
                {p.name}
                {p.rating ? (
                  <span className="ml-1.5 text-primary">
                    <span aria-hidden="true">★</span> {p.rating}
                    <span className="sr-only"> of 5</span>
                  </span>
                ) : (
                  <span className="ml-1.5 text-muted-foreground">· not rated</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </Link>
    </li>
  )
}

export function HistoryPage() {
  const history = useInfiniteQuery({
    queryKey: ['history', 'list'],
    queryFn: ({ pageParam }) => api.history(pageParam, PAGE_SIZE),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => (last.has_more ? pages.length * PAGE_SIZE : undefined),
  })
  const items = history.data?.pages.flatMap((page) => page.items) ?? []

  let content
  if (history.isPending) {
    content = (
      <div role="status" aria-label="Loading history" className="space-y-4">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-28 animate-pulse rounded-3xl bg-card shadow-soft" />
        ))}
      </div>
    )
  } else if (history.isError && items.length === 0) {
    content = (
      <div className={`${CARD} space-y-4`}>
        <FormMessage kind="error">{history.error.message}</FormMessage>
        <Button className="rounded-full px-6" onClick={() => history.refetch()}>
          Try again
        </Button>
      </div>
    )
  } else if (items.length === 0) {
    content = (
      <div className={CARD}>
        <h2 className="font-display text-2xl font-medium">Nothing here yet</h2>
        <p className="mt-2 text-muted-foreground">
          Your symptoms and the points you were given will appear here.
        </p>
        <Button asChild className="mt-5 rounded-full px-6">
          <Link to="/">Find points</Link>
        </Button>
      </div>
    )
  } else {
    content = (
      <>
        <ul className="space-y-4">
          {items.map((item) => (
            <HistoryRow key={item.attempt_id} item={item} />
          ))}
        </ul>
        {history.isFetchNextPageError && (
          <div className="mt-4">
            <FormMessage kind="error">{history.error?.message}</FormMessage>
          </div>
        )}
        {history.hasNextPage && (
          <Button
            variant="outline"
            className="mt-6 rounded-full px-6"
            disabled={history.isFetchingNextPage}
            onClick={() => history.fetchNextPage()}
          >
            {history.isFetchingNextPage ? 'Loading…' : 'Show more'}
          </Button>
        )}
      </>
    )
  }

  return (
    <SplitLayout
      nav={<AppNav />}
      aside={
        <>
          <h1 className="font-display text-4xl font-medium leading-tight lg:text-5xl">Your history</h1>
          <p className="mt-3 text-muted-foreground">
            Look back at the symptoms you described and the points you were given. Open one to see
            the instructions again or to rate a point you've tried.
          </p>
        </>
      }
    >
      <section aria-label="Past recommendations" className="mx-auto max-w-2xl">
        {content}
      </section>
    </SplitLayout>
  )
}
