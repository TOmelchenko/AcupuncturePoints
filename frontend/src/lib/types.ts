// Mirrors the backend API contract (backend/app/schemas.py, see /docs).

export interface RecommendedPoint {
  point_id: string
  rank: number
  name: string
  location_text: string
  image_url: string | null
  image_attribution: string | null
  instructions: string[]
  duration: string | null
  pressure: string | null
}

export type RecommendationResponse =
  | { outcome: 'recommended'; attempt_id: string; points: RecommendedPoint[] }
  | { outcome: 'clarification_needed'; attempt_id: string; question: string }
  | { outcome: 'no_match'; attempt_id: string; message: string }

export interface FeedbackResponse {
  attempt_id: string
  point_id: string
  rating: number
}

export interface ErrorBody {
  code: string
  message: string
  retryable: boolean
}
