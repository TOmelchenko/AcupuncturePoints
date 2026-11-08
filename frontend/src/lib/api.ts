import { supabase } from './supabase'
import type { ErrorBody, FeedbackResponse, RecommendationResponse } from './types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
const FALLBACK_MESSAGE = 'Something went wrong. Please try again.'

/** An error from the API, carrying the backend's safe, user-facing message. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly retryable: boolean

  constructor(status: number, body: ErrorBody) {
    super(body.message)
    this.status = status
    this.code = body.code
    this.retryable = body.retryable
  }
}

async function request<T>(path: string, method: string, body?: unknown): Promise<T> {
  const { data } = await supabase.auth.getSession()
  const headers: Record<string, string> = {}
  if (data.session) headers.Authorization = `Bearer ${data.session.access_token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, { code: 'network_error', message: FALLBACK_MESSAGE, retryable: true })
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const error: ErrorBody = payload?.error ?? {
      code: 'internal_error',
      message: FALLBACK_MESSAGE,
      retryable: response.status >= 500,
    }
    throw new ApiError(response.status, error)
  }
  return (response.status === 204 ? undefined : await response.json()) as T
}

export const api = {
  recommend: (symptom: string) =>
    request<RecommendationResponse>('/api/recommendations', 'POST', { symptom }),
  clarify: (attemptId: string, answer: string) =>
    request<RecommendationResponse>(`/api/recommendations/${attemptId}/clarification`, 'POST', {
      answer,
    }),
  rate: (attemptId: string, pointId: string, rating: number) =>
    request<FeedbackResponse>(
      `/api/recommendations/${attemptId}/points/${encodeURIComponent(pointId)}/feedback`,
      'POST',
      { rating },
    ),
  deleteAccount: () => request<void>('/api/account', 'DELETE'),
}
