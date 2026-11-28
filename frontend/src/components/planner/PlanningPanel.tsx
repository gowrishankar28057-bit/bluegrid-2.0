import { useEffect, useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ArrowRight, LoaderCircle, X } from 'lucide-react'
import { evaluateScenario } from '../../services/api'
import type { ScenarioEvaluation } from '../../services/api'
import type { Location } from '../../types/location'

interface PlanningPanelProps {
  location: Location
  onClose: () => void
}

const fields = [
  { key: 'demandKw', label: 'Electricity demand', unit: 'kW', initial: '100', min: 0.01, max: 1e6 },
  { key: 'floatingSolarKw', label: 'Floating solar', unit: 'kW', initial: '200', min: 0, max: 1e7 },
  { key: 'onshoreWindKw', label: 'Onshore wind', unit: 'kW', initial: '200', min: 0, max: 1e7 },
  { key: 'otecKw', label: 'OTEC', unit: 'kW', initial: '50', min: 0, max: 1e7 },
  { key: 'batteryKwh', label: 'Battery storage', unit: 'kWh', initial: '600', min: 0, max: 1e7 },
] as const

type FieldKey = typeof fields[number]['key']
const initialValues = Object.fromEntries(fields.map(field => [field.key, field.initial])) as Record<FieldKey, string>
const number = (value: number, digits = 1) => value.toLocaleString('en', { maximumFractionDigits: digits })

export default function PlanningPanel({ location, onClose }: PlanningPanelProps) {
  const id = useId()
  const dialogRef = useRef<HTMLDialogElement>(null)
  const firstInputRef = useRef<HTMLInputElement>(null)
  const requestRef = useRef<AbortController | null>(null)
  const [values, setValues] = useState(initialValues)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ScenarioEvaluation | null>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (dialog && !dialog.open) dialog.showModal()
    firstInputRef.current?.focus()
    setResult(null)
    setError(null)
    setIsLoading(false)
    return () => {
      requestRef.current?.abort()
      dialog?.close()
    }
  }, [location.id])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const parsed = {} as Record<FieldKey, number>
    for (const field of fields) {
      const value = Number(values[field.key])
      if (!values[field.key].trim() || !Number.isFinite(value) || value < field.min || value > field.max) {
        setError(`${field.label} must be between ${number(field.min, 2)} and ${number(field.max, 0)} ${field.unit}.`)
        return
      }
      parsed[field.key] = value
    }
    requestRef.current?.abort()
    const controller = new AbortController()
    requestRef.current = controller
    setIsLoading(true)
    setError(null)
    setResult(null)
    try {
      const evaluation = await evaluateScenario({
        scenario: {
          location_id: location.id,
          demand_kw: parsed.demandKw,
          capacities_kw: {
            floating_solar: parsed.floatingSolarKw,
            onshore_wind: parsed.onshoreWindKw,
            otec: parsed.otecKw,
          },
          battery_kwh: parsed.batteryKwh,
          max_lpsp: 0.05,
        },
        include_hourly: false,
      }, controller.signal)
      if (!controller.signal.aborted) setResult(evaluation)
    } catch (failure) {
      if (!controller.signal.aborted) {
        setError(failure instanceof Error ? failure.message : 'The evaluation could not be completed. Please try again.')
      }
    } finally {
      if (!controller.signal.aborted) setIsLoading(false)
    }
  }

  return (
    <dialog
      className="planning-overlay"
      ref={dialogRef}
      aria-labelledby={`${id}-title`}
      aria-describedby={`${id}-description`}
      onCancel={event => { event.preventDefault(); onClose() }}
      onClick={event => { if (event.target === event.currentTarget) onClose() }}
    >
      <section className="planning-panel">
        <header className="planning-header">
          <div>
            <p className="planning-badge">Synthetic demonstration resources</p>
            <h2 id={`${id}-title`}>Plan for {location.name}</h2>
          </div>
          <button type="button" className="planning-close" aria-label="Close energy planner" onClick={onClose}>
            <X size={20} aria-hidden="true" />
          </button>
        </header>
        <p id={`${id}-description`} className="planning-note">
          Evaluate an initial energy mix using synthetic annual resources and illustrative costs.
        </p>
        <form onSubmit={submit} aria-busy={isLoading}>
          <div className="planning-grid">
            {fields.map(field => (
              <label className="planning-field" htmlFor={`${id}-${field.key}`} key={field.key}>
                <span>{field.label} <span>({field.unit})</span></span>
                <input
                  ref={field.key === 'demandKw' ? firstInputRef : undefined}
                  className="planning-input"
                  id={`${id}-${field.key}`}
                  name={field.key}
                  type="number"
                  inputMode="decimal"
                  min={field.min}
                  max={field.max}
                  step="any"
                  required
                  value={values[field.key]}
                  disabled={isLoading}
                  onChange={event => {
                    setValues(previous => ({ ...previous, [field.key]: event.target.value }))
                    setError(null)
                    setResult(null)
                  }}
                />
              </label>
            ))}
          </div>
          <p className="planning-note">Reliability target: at most 5% unmet annual energy. Battery and financial assumptions use the engine defaults.</p>
          {error && <p className="planning-error" role="alert">{error}</p>}
          <div className="planning-actions">
            <button className="planning-submit" type="submit" disabled={isLoading}>
              {isLoading ? <LoaderCircle size={17} aria-hidden="true" /> : <ArrowRight size={17} aria-hidden="true" />}
              {isLoading ? 'Evaluating configuration…' : error ? 'Retry evaluation' : 'Evaluate configuration'}
            </button>
            <button type="button" onClick={onClose}>Close</button>
          </div>
          <span className="sr-only" role="status">{isLoading ? 'Evaluation in progress.' : ''}</span>
        </form>
        {result && (
          <section className="planning-result" aria-labelledby={`${id}-result-title`} role="status">
            <h3 id={`${id}-result-title`}>{result.feasible ? 'Modeled reliability target met' : 'Modeled reliability target not met'}</h3>
            <dl className="planning-results-grid">
              <div><dt>Unmet energy · LPSP</dt><dd>{number(result.metrics.lpsp * 100, 2)}%</dd></div>
              <div><dt>Annual energy served</dt><dd>{number(result.metrics.energy_served_kwh / 1000)} MWh</dd></div>
              <div><dt>CAPEX · {result.economics.currency}</dt><dd>{number(result.economics.capex, 0)}</dd></div>
              <div><dt>LCOE · {result.economics.currency}/kWh</dt><dd>{result.economics.lcoe === null ? 'Not defined' : number(result.economics.lcoe, 2)}</dd></div>
            </dl>
            <p className="planning-note">{result.provenance.synthetic ? 'Synthetic resource model' : 'Resource model'} with illustrative costs. This result does not establish site feasibility.</p>
            {result.warnings.length > 0 && <details><summary>Model assumptions</summary><ul>{result.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul></details>}
          </section>
        )}
      </section>
    </dialog>
  )
}
