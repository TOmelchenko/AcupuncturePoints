import type { ReactNode } from 'react'
import type { RecommendedPoint } from '@/lib/types'

interface Props {
  point: RecommendedPoint
  index: number
  /** Footer content, e.g. the rating control. */
  footer?: ReactNode
}

function Visual({ point }: { point: RecommendedPoint }) {
  if (point.image_url) {
    return (
      <figure>
        <img
          src={point.image_url}
          alt={`Location of ${point.name}`}
          loading="lazy"
          className="aspect-square w-full rounded-2xl bg-secondary object-contain"
        />
        {point.image_attribution && (
          <figcaption className="mt-1.5 text-[11px] leading-snug text-muted-foreground">
            {point.image_attribution}
          </figcaption>
        )}
      </figure>
    )
  }
  return (
    <div
      aria-hidden="true"
      className="flex aspect-square items-center justify-center rounded-2xl bg-secondary p-2 text-center font-display text-2xl font-semibold text-secondary-foreground"
    >
      {point.point_id}
    </div>
  )
}

/** One recommended point: curated picture (or code tile), location, steps and optional guidance. */
export function PointCard({ point, index, footer }: Props) {
  const headingId = `point-${point.point_id}`
  return (
    <article
      aria-labelledby={headingId}
      style={{ animationDelay: `${index * 120}ms` }}
      className="animate-rise grid gap-5 rounded-3xl border border-border bg-card p-6 shadow-soft sm:grid-cols-[140px_1fr]"
    >
      <div className="mx-auto w-full max-w-[200px] sm:max-w-none">
        <Visual point={point} />
      </div>
      <div>
        <p className="text-xs font-medium uppercase tracking-widest text-primary">{point.point_id}</p>
        <h3 id={headingId} className="font-display text-xl font-medium">
          {point.name}
        </h3>
        <p className="mt-2 text-sm">
          <span className="font-medium">Where: </span>
          <span className="text-muted-foreground">{point.location_text}</span>
        </p>
        <div className="mt-3 text-sm">
          <p className="font-medium">How to apply pressure:</p>
          <ol className="mt-1 list-decimal space-y-1 pl-5 text-muted-foreground">
            {point.instructions.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        </div>
        {(point.duration || point.pressure) && (
          <dl className="mt-3 flex flex-wrap gap-2 text-xs">
            {point.duration && (
              <div className="rounded-full bg-secondary px-3 py-1 text-secondary-foreground">
                <dt className="inline font-medium">Duration: </dt>
                <dd className="inline">{point.duration}</dd>
              </div>
            )}
            {point.pressure && (
              <div className="rounded-full bg-secondary px-3 py-1 text-secondary-foreground">
                <dt className="inline font-medium">Pressure: </dt>
                <dd className="inline">{point.pressure}</dd>
              </div>
            )}
          </dl>
        )}
        {footer && <div className="mt-4 border-t border-border pt-3">{footer}</div>}
      </div>
    </article>
  )
}
