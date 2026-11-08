import type { RecommendedPoint } from '@/lib/types'
import { PointCard } from './PointCard'
import { StarRating } from './StarRating'

interface Props {
  attemptId: string
  points: RecommendedPoint[]
}

export function RecommendationList({ attemptId, points }: Props) {
  return (
    <div className="mt-8 space-y-5">
      {points.map((point, index) => (
        <PointCard
          key={point.point_id}
          point={point}
          index={index}
          footer={<StarRating attemptId={attemptId} pointId={point.point_id} pointName={point.name} />}
        />
      ))}
    </div>
  )
}
