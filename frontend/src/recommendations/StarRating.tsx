import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

interface Props {
  attemptId: string
  pointId: string
  pointName: string
  /** A rating saved earlier, shown as selected. */
  initialRating?: number | null
}

/**
 * A 1–5 star rating saved independently for one point. Built on native radio
 * inputs, so it works with Tab and the arrow keys and is announced correctly.
 */
export function StarRating({ attemptId, pointId, pointName, initialRating }: Props) {
  const queryClient = useQueryClient()
  const [hovered, setHovered] = useState(0)
  const [selected, setSelected] = useState(initialRating ?? 0)
  const save = useMutation({
    mutationFn: (rating: number) => api.rate(attemptId, pointId, rating),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['history'] }),
  })
  const shown = hovered || selected
  const name = `rating-${attemptId}-${pointId}`

  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <fieldset className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <legend className="float-left mr-3 text-xs text-muted-foreground">
          Tried it? Rate it<span className="sr-only">: how helpful was {pointName}?</span>
        </legend>
        <div className="flex" onMouseLeave={() => setHovered(0)}>
          {[1, 2, 3, 4, 5].map((n) => (
            <label key={n} className="cursor-pointer" onMouseEnter={() => setHovered(n)}>
              <input
                type="radio"
                name={name}
                value={n}
                checked={selected === n}
                onChange={() => {
                  setSelected(n)
                  save.mutate(n)
                }}
                className="peer sr-only"
              />
              <span
                aria-hidden="true"
                className={cn(
                  'block rounded px-0.5 text-xl leading-none transition-colors peer-focus-visible:ring-2 peer-focus-visible:ring-ring',
                  n <= shown ? 'text-primary' : 'text-border',
                )}
              >
                ★
              </span>
              <span className="sr-only">{n === 1 ? '1 star' : `${n} stars`}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <p aria-live="polite" className="text-xs">
        {save.isPending && <span className="text-muted-foreground">Saving…</span>}
        {save.isSuccess && <span className="text-primary">Thanks — saved</span>}
        {save.isError && (
          <span className="text-destructive">
            Couldn't save your rating.{' '}
            <button type="button" className="underline" onClick={() => save.mutate(selected)}>
              Try again
            </button>
          </span>
        )}
      </p>
    </div>
  )
}
