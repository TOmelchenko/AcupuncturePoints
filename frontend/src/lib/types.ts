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

export type HistoryOutcome = 'recommended' | 'clarification_needed' | 'no_match'

export interface HistoryItem {
  attempt_id: string
  created_at: string
  symptom: string
  outcome: HistoryOutcome
  points: { point_id: string; name: string; rating: number | null }[]
}

export interface HistoryPage {
  items: HistoryItem[]
  has_more: boolean
}

export interface RatedPoint extends RecommendedPoint {
  rating: number | null
}

export interface HistoryDetail {
  attempt_id: string
  created_at: string
  symptom: string
  outcome: HistoryOutcome
  clarification_question: string | null
  clarification_answer: string | null
  points: RatedPoint[]
}

export interface ErrorBody {
  code: string
  message: string
  retryable: boolean
}
