import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { AppNav } from '@/components/AppNav'
import { Disclaimer } from '@/components/Disclaimer'
import { FormMessage } from '@/components/FormMessage'
import { SplitLayout } from '@/components/SplitLayout'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import type { RecommendationResponse } from '@/lib/types'
import { ClarificationForm } from '@/recommendations/ClarificationForm'
import { RecommendationList } from '@/recommendations/RecommendationList'
import { SymptomForm } from '@/recommendations/SymptomForm'

type Request = { kind: 'symptom'; symptom: string } | { kind: 'answer'; attemptId: string; answer: string }

function send(request: Request): Promise<RecommendationResponse> {
  return request.kind === 'symptom'
    ? api.recommend(request.symptom)
    : api.clarify(request.attemptId, request.answer)
}

function Placeholder() {
  return (
    <div className="animate-rise">
      <p className="text-sm font-medium uppercase tracking-widest text-primary">How it works</p>
      <h2 className="mt-2 font-display text-3xl font-medium">Three points to try</h2>
      <ol className="mt-6 space-y-3 text-muted-foreground">
        <li>1. Describe a physical or emotional symptom in your own words.</li>
        <li>2. We match it against curated acupressure knowledge — and ask if anything is unclear.</li>
        <li>3. You get three points with where to find them and how to apply pressure.</li>
      </ol>
    </div>
  )
}

function Loading() {
  return (
    <div role="status" aria-live="polite">
      <p className="text-sm font-medium uppercase tracking-widest text-primary">Finding points…</p>
      <div className="mt-8 space-y-5" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-40 animate-pulse rounded-3xl bg-card shadow-soft" />
        ))}
      </div>
    </div>
  )
}

export function HomePage() {
  const [symptom, setSymptom] = useState('')
  const recommendation = useMutation({ mutationFn: send })
  const { data, error, isPending } = recommendation
  const lastRequest = recommendation.variables

  const submitSymptom = (text: string) => {
    setSymptom(text)
    recommendation.mutate({ kind: 'symptom', symptom: text })
  }

  let content
  if (isPending) {
    content = <Loading />
  } else if (error) {
    content = (
      <div className="animate-rise space-y-4 rounded-3xl border border-border bg-card p-6 shadow-soft sm:p-8">
        <FormMessage kind="error">{error.message}</FormMessage>
        <Button className="rounded-full px-6" onClick={() => lastRequest && recommendation.mutate(lastRequest)}>
          Try again
        </Button>
      </div>
    )
  } else if (data?.outcome === 'clarification_needed') {
    content = (
      <ClarificationForm
        question={data.question}
        busy={isPending}
        onSubmit={(answer) => recommendation.mutate({ kind: 'answer', attemptId: data.attempt_id, answer })}
      />
    )
  } else if (data?.outcome === 'no_match') {
    content = (
      <section aria-labelledby="no-match-heading" className="animate-rise rounded-3xl border border-border bg-card p-6 shadow-soft sm:p-8">
        <h2 id="no-match-heading" className="font-display text-2xl font-medium">No suitable points found</h2>
        <p className="mt-3 text-muted-foreground">{data.message}</p>
        <Button variant="outline" className="mt-5 rounded-full px-6" onClick={() => recommendation.reset()}>
          Try a different description
        </Button>
      </section>
    )
  } else if (data?.outcome === 'recommended') {
    content = (
      <section aria-labelledby="results-heading">
        <p className="text-sm font-medium uppercase tracking-widest text-primary">Three points to try</p>
        <h2 id="results-heading" className="mt-2 font-display text-3xl font-medium">
          For “{symptom}”
        </h2>
        <RecommendationList attemptId={data.attempt_id} points={data.points} />
        <Disclaimer className="mt-8" />
      </section>
    )
  } else {
    content = <Placeholder />
  }

  return (
    <SplitLayout
      nav={<AppNav />}
      aside={
        <>
          <h1 className="font-display text-4xl font-medium leading-tight lg:text-5xl">How are you feeling today?</h1>
          <p className="mt-3 text-muted-foreground">
            Describe a physical or emotional symptom in your own words, and we'll suggest three
            acupressure points you can try yourself.
          </p>
          <SymptomForm onSubmit={submitSymptom} busy={isPending} />
        </>
      }
    >
      <div aria-live="polite">{content}</div>
    </SplitLayout>
  )
}
