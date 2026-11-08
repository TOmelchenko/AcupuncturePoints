import type { RecommendedPoint } from '@/lib/types'

interface Props {
  attemptId: string
  points: RecommendedPoint[]
}

export function RecommendationList({ points }: Props) {
  return (
    <ol className="mt-8 space-y-5">
      {points.map((point) => (
        <li key={point.point_id}>{point.name}</li>
      ))}
    </ol>
  )
}
