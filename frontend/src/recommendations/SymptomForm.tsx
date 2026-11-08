import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { symptomSchema, type SymptomValues } from './schemas'

interface Props {
  onSubmit: (symptom: string) => void
  busy: boolean
}

export function SymptomForm({ onSubmit, busy }: Props) {
  const { register, handleSubmit, formState } = useForm<SymptomValues>({
    resolver: zodResolver(symptomSchema),
  })
  const error = formState.errors.symptom?.message

  return (
    <form onSubmit={handleSubmit((v) => onSubmit(v.symptom))} noValidate className="mt-6 space-y-3">
      <Label htmlFor="symptom" className="sr-only">
        Describe your symptom
      </Label>
      <textarea
        id="symptom"
        rows={3}
        placeholder="For example: tension headache behind my eyes after long screen time"
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? 'symptom-error' : undefined}
        className="w-full resize-none rounded-2xl border border-input bg-card p-4 shadow-soft outline-none focus:ring-2 focus:ring-ring"
        {...register('symptom')}
      />
      {error && (
        <p id="symptom-error" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <Button type="submit" disabled={busy} className="h-12 w-full rounded-full text-base">
        {busy ? 'Finding points…' : 'Find points'}
      </Button>
    </form>
  )
}
