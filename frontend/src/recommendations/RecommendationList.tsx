import type { RecommendedPoint } from '@/lib/types'
import { PointCard } from './PointCard'

interface Props {
  attemptId: string
  points: RecommendedPoint[]
}

export function RecommendationList({ points }: Props) {
  return (
    <div className="mt-8 space-y-5">
      {points.map((point, index) => (
        <PointCard key={point.point_id} point={point} index={index} />
      ))}
    </div>
  )
}
