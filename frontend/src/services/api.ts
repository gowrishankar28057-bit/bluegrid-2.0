export interface ScenarioEvaluationRequest {
  scenario: {
    location_id: string
    demand_kw: number
    capacities_kw: {
      floating_solar: number
      onshore_wind: number
      otec: number
    }
    battery_kwh: number
    max_lpsp: number
  }
  include_hourly: false
}

export interface ScenarioEvaluation {
  metrics: {
    lpsp: number
    energy_served_kwh: number
  }
  economics: {
    capex: number
    lcoe: number | null
    currency: string
  }
  feasible: boolean
  provenance: { synthetic: boolean }
  warnings: string[]
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function nonnegativeNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0
}

function parseEvaluation(value: unknown): ScenarioEvaluation {
  if (!isRecord(value) || !isRecord(value.metrics) || !isRecord(value.economics)
    || !isRecord(value.provenance)) {
    throw new Error('The evaluation service returned an incomplete result. Please try again.')
  }
  const { metrics, economics, provenance } = value
  if (!nonnegativeNumber(metrics.lpsp) || metrics.lpsp > 1
    || !nonnegativeNumber(metrics.energy_served_kwh)
    || !nonnegativeNumber(economics.capex)
    || !(economics.lcoe === null || nonnegativeNumber(economics.lcoe))
    || typeof economics.currency !== 'string' || !/^[A-Z]{3}$/.test(economics.currency)
    || typeof value.feasible !== 'boolean' || typeof provenance.synthetic !== 'boolean') {
    throw new Error('The evaluation service returned an invalid result. Please try again.')
  }
  return {
    metrics: { lpsp: metrics.lpsp, energy_served_kwh: metrics.energy_served_kwh },
    economics: { capex: economics.capex, lcoe: economics.lcoe, currency: economics.currency },
    feasible: value.feasible,
    provenance: { synthetic: provenance.synthetic },
    warnings: Array.isArray(value.warnings)
      ? value.warnings.filter((warning): warning is string => typeof warning === 'string') : [],
  }
}

export async function evaluateScenario(
  body: ScenarioEvaluationRequest,
  signal?: AbortSignal,
): Promise<ScenarioEvaluation> {
  let response: Response
  try {
    response = await fetch('/api/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
      signal,
    })
  } catch (error) {
    if (signal?.aborted) throw error
    throw new Error('The evaluation service is unavailable. Please try again when it is connected.')
  }
  let payload: unknown
  try {
    payload = await response.json()
  } catch (error) {
    if (signal?.aborted) throw error
    throw new Error(response.ok
      ? 'The evaluation service returned an unreadable result. Please try again.'
      : `The evaluation service could not complete this request (${response.status}). Please try again.`)
  }
  if (!response.ok) {
    const error = isRecord(payload) && isRecord(payload.error) ? payload.error : null
    throw new Error(error && typeof error.message === 'string'
      ? error.message : `The evaluation could not be completed (${response.status}). Please try again.`)
  }
  return parseEvaluation(payload)
}
