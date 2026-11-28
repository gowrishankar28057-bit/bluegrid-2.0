import { afterEach, describe, expect, it, vi } from 'vitest'
import { evaluateScenario } from './api'
import type { ScenarioEvaluationRequest } from './api'

const request: ScenarioEvaluationRequest = {
  scenario: {
    location_id: 'lakshadweep', demand_kw: 100,
    capacities_kw: { floating_solar: 200, onshore_wind: 200, otec: 50 },
    battery_kwh: 600, max_lpsp: 0.05,
  },
  include_hourly: false,
}

function result() {
  return {
    metrics: { lpsp: 0.02, energy_served_kwh: 858480 },
    economics: { capex: 12345678, lcoe: 17.89, currency: 'INR' },
    feasible: true, provenance: { synthetic: true }, warnings: ['Illustrative test assumptions.'],
  }
}

function respond(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status, headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => vi.unstubAllGlobals())

describe('evaluateScenario', () => {
  it('posts the scenario and abort signal, then returns the service values', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(respond(result()))
    vi.stubGlobal('fetch', fetchMock)
    const controller = new AbortController()
    const actual = await evaluateScenario(request, controller.signal)
    expect(actual).toEqual(result())
    expect(fetchMock).toHaveBeenCalledOnce()
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/evaluate')
    expect(options?.method).toBe('POST')
    expect(options?.signal).toBe(controller.signal)
    expect(options?.headers).toEqual({ 'Content-Type': 'application/json', Accept: 'application/json' })
    expect(JSON.parse(options?.body as string)).toEqual(request)
  })

  it('preserves an explicitly undefined LCOE represented by null', async () => {
    const payload = { ...result(), economics: { ...result().economics, lcoe: null } }
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(respond(payload)))
    expect((await evaluateScenario(request)).economics.lcoe).toBeNull()
  })

  it.each([
    ['missing economics', { ...result(), economics: undefined }],
    ['invalid LPSP', { ...result(), metrics: { lpsp: 1.1, energy_served_kwh: 1 } }],
    ['negative energy', { ...result(), metrics: { lpsp: 0, energy_served_kwh: -1 } }],
    ['nonfinite CAPEX', { ...result(), economics: { ...result().economics, capex: Infinity } }],
    ['negative LCOE', { ...result(), economics: { ...result().economics, lcoe: -1 } }],
    ['invalid currency', { ...result(), economics: { ...result().economics, currency: '<script>' } }],
    ['untyped feasibility', { ...result(), feasible: 'true' }],
    ['missing resource provenance', { ...result(), provenance: {} }],
  ])('rejects %s instead of presenting it as a result', async (_label, payload) => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(respond(payload)))
    await expect(evaluateScenario(request)).rejects.toThrow(/incomplete result|invalid result/)
  })

  it('uses a structured backend error message for failed requests', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(
      respond({ error: { message: 'annual demand must be greater than zero' } }, 400),
    ))
    await expect(evaluateScenario(request)).rejects.toThrow('annual demand must be greater than zero')
  })

  it('gives a useful fallback for a failed response without the error envelope', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(respond({}, 503)))
    await expect(evaluateScenario(request)).rejects.toThrow(/503/)
  })

  it('handles an unavailable service', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(evaluateScenario(request)).rejects.toThrow('The evaluation service is unavailable.')
  })

  it('rejects a successful HTTP response containing non-JSON content', async () => {
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockResolvedValue(new Response('<html>Proxy error</html>')))
    await expect(evaluateScenario(request)).rejects.toThrow(/unreadable result/)
  })

  it('preserves request cancellation rather than replacing it with a network error', async () => {
    const controller = new AbortController()
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockImplementation((_url, options) => new Promise((_resolve, reject) => {
      options?.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true })
    })))
    const pending = evaluateScenario(request, controller.signal)
    const rejection = expect(pending).rejects.toMatchObject({ name: 'AbortError' })
    controller.abort()
    await rejection
  })
})
