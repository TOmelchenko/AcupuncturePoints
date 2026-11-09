import { useEffect, useState, type ReactNode } from 'react'
import { X } from 'lucide-react'
import type { RecommendedPoint } from '@/lib/types'

interface Props {
  point: RecommendedPoint
  index: number
  /** Footer content, e.g. the rating control. */
  footer?: ReactNode
}

/** Full-screen view of a point image; closes on click, the close button or Escape. */
function ImageZoom({ src, alt, onClose }: { src: string; alt: string; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = overflow
    }
  }, [onClose])

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={alt}
      onClick={onClose}
      className="fixed inset-0 z-50 flex cursor-zoom-out items-center justify-center bg-black/80 p-4 animate-in fade-in-0"
    >
      <button
        type="button"
        autoFocus
        aria-label="Close enlarged image"
        onClick={onClose}
        className="absolute right-4 top-4 rounded-full bg-card p-2 text-foreground shadow-soft"
      >
        <X className="size-5" />
      </button>
      <img src={src} alt={alt} className="max-h-full max-w-full rounded-2xl bg-secondary object-contain" />
    </div>
  )
}

function Visual({ point }: { point: RecommendedPoint }) {
  const [zoomed, setZoomed] = useState(false)
  if (point.image_url) {
    const alt = `Location of ${point.name}`
    return (
      <figure>
        <button
          type="button"
          onClick={() => setZoomed(true)}
          aria-label={`Enlarge image of ${point.name}`}
          className="block w-full cursor-zoom-in rounded-2xl"
        >
          <img
            src={point.image_url}
            alt={alt}
            loading="lazy"
            className="aspect-square w-full rounded-2xl bg-secondary object-contain"
          />
        </button>
        {point.image_attribution && (
          <figcaption className="mt-1.5 text-[11px] leading-snug text-muted-foreground">
            {point.image_attribution}
          </figcaption>
        )}
        {zoomed && <ImageZoom src={point.image_url} alt={alt} onClose={() => setZoomed(false)} />}
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
