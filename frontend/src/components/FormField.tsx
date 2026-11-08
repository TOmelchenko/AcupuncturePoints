import type { InputHTMLAttributes } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  id: string
  label: string
  error?: string
}

/** A labelled input whose validation error is announced to screen readers. */
export function FormField({ id, label, error, ...input }: Props) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        className="h-11 rounded-xl bg-card"
        {...input}
      />
      {error && (
        <p id={`${id}-error`} className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}
