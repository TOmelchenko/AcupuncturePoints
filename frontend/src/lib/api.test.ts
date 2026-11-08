import { api, ApiError } from './api'

const getSession = vi.fn()
vi.mock('./supabase', () => ({ supabase: { auth: { getSession: () => getSession() } } }))

function respond(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue(
    new Response(body === undefined ? null : JSON.stringify(body), { status }),
  )
}

beforeEach(() => {
  getSession.mockResolvedValue({ data: { session: { access_token: 'tok-123' } } })
})

afterEach(() => vi.unstubAllGlobals())

test('sends the access token and JSON body', async () => {
  const fetchMock = respond(200, { outcome: 'no_match', attempt_id: 'a1', message: 'none' })
  vi.stubGlobal('fetch', fetchMock)

  const result = await api.recommend('sore neck')

  expect(result).toEqual({ outcome: 'no_match', attempt_id: 'a1', message: 'none' })
  const [url, init] = fetchMock.mock.calls[0]
  expect(url).toBe('/api/recommendations')
  expect(init.method).toBe('POST')
  expect(init.headers.Authorization).toBe('Bearer tok-123')
  expect(JSON.parse(init.body)).toEqual({ symptom: 'sore neck' })
})

test('turns the common error shape into an ApiError with the safe message', async () => {
  vi.stubGlobal(
    'fetch',
    respond(502, {
      error: { code: 'recommendation_failed', message: 'Please try again.', retryable: true },
    }),
  )

  const error = await api.recommend('sore neck').catch((e: unknown) => e)

  expect(error).toBeInstanceOf(ApiError)
  expect(error).toMatchObject({
    status: 502,
    code: 'recommendation_failed',
    message: 'Please try again.',
    retryable: true,
  })
})

test('network failures become a retryable generic error', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
  await expect(api.recommend('x')).rejects.toMatchObject({ code: 'network_error', retryable: true })
})

test('non-JSON errors get a generic message', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>', { status: 500 })))
  await expect(api.recommend('x')).rejects.toMatchObject({
    message: 'Something went wrong. Please try again.',
    retryable: true,
  })
})

test('point ids are URL-encoded and 204 responses resolve empty', async () => {
  const fetchMock = respond(200, { attempt_id: 'a1', point_id: 'EX-HN3', rating: 4 })
  vi.stubGlobal('fetch', fetchMock)
  await api.rate('a1', 'EX/HN3', 4)
  expect(fetchMock.mock.calls[0][0]).toBe('/api/recommendations/a1/points/EX%2FHN3/feedback')

  vi.stubGlobal('fetch', respond(204))
  await expect(api.deleteAccount()).resolves.toBeUndefined()
})
