import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { answerSchema, type AnswerValues } from './schemas'

interface Props {
  question: string
  onSubmit: (answer: string) => void
  busy: boolean
}

export function ClarificationForm({ question, onSubmit, busy }: Props) {
  const { register, handleSubmit, formState } = useForm<AnswerValues>({ resolver: zodResolver(answerSchema) })
  const error = formState.errors.answer?.message

  return (
    <section aria-labelledby="clarify-heading" className="animate-rise rounded-3xl border border-border bg-card p-6 shadow-soft sm:p-8">
      <p className="text-sm font-medium uppercase tracking-widest text-primary">One more question</p>
      <h2 id="clarify-heading" className="mt-2 font-display text-2xl font-medium">
        {question}
      </h2>
      <form onSubmit={handleSubmit((v) => onSubmit(v.answer))} noValidate className="mt-5 space-y-3">
        <Label htmlFor="answer">Your answer</Label>
        <textarea
          id="answer"
          rows={3}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? 'answer-error' : undefined}
          className="w-full resize-none rounded-2xl border border-input bg-background p-4 outline-none focus:ring-2 focus:ring-ring"
          {...register('answer')}
        />
        {error && (
          <p id="answer-error" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <Button type="submit" disabled={busy} className="h-11 rounded-full px-6">
          {busy ? 'Finding points…' : 'Continue'}
        </Button>
      </form>
    </section>
  )
}
