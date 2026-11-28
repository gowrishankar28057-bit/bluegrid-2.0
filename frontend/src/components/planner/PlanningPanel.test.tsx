import { useState } from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import PlanningPanel from './PlanningPanel'
import type { Location } from '../../types/location'

const location: Location = {
  id: 'lakshadweep', name: 'Lakshadweep', country: 'India', region: 'Arabian Sea',
  latitude: 10.57, longitude: 72.64, description: 'Island demonstration location',
  technologies: ['Floating solar', 'Onshore wind', 'OTEC'], timezone: 'Asia/Kolkata',
}

function response() {
  return new Response(JSON.stringify({
    metrics: { lpsp: 0.02, energy_served_kwh: 858480 },
    economics: { capex: 12345678, lcoe: 17.89, currency: 'INR' },
    feasible: true, provenance: { synthetic: true },
    warnings: ['Test resource profiles are synthetic.'],
  }), { status: 200, headers: { 'Content-Type': 'application/json' } })
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('PlanningPanel', () => {
  it('opens a named dialog with labelled unit-bearing inputs and focuses demand', () => {
    render(<PlanningPanel location={location} onClose={vi.fn()} />)
    const dialog = screen.getByRole('dialog', { name: 'Plan for Lakshadweep' })
    expect((dialog as HTMLDialogElement).open).toBe(true)
    const demand = screen.getByRole('spinbutton', { name: 'Electricity demand (kW)' })
    expect(document.activeElement).toBe(demand)
    expect((demand as HTMLInputElement).value).toBe('100')
    expect((screen.getByRole('spinbutton', { name: 'Battery storage (kWh)' }) as HTMLInputElement).value).toBe('600')
    expect(screen.getByText('Synthetic demonstration resources')).toBeTruthy()
    expect(screen.queryByText(/Modeled reliability target met/)).toBeNull()
  })

  it('submits edited capacities and displays actual returned metrics', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(response())
    vi.stubGlobal('fetch', fetchMock)
    render(<PlanningPanel location={location} onClose={vi.fn()} />)
    const solar = screen.getByRole('spinbutton', { name: 'Floating solar (kW)' })
    const battery = screen.getByRole('spinbutton', { name: 'Battery storage (kWh)' })
    await user.clear(solar)
    await user.type(solar, '345.5')
    await user.clear(battery)
    await user.type(battery, '900')
    await user.click(screen.getByRole('button', { name: 'Evaluate configuration' }))
    await screen.findByRole('heading', { name: 'Modeled reliability target met' })
    expect(fetchMock).toHaveBeenCalledOnce()
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/evaluate')
    expect(JSON.parse(options?.body as string)).toEqual({
      scenario: {
        location_id: 'lakshadweep', demand_kw: 100,
        capacities_kw: { floating_solar: 345.5, onshore_wind: 200, otec: 50 },
        battery_kwh: 900, max_lpsp: 0.05,
      },
      include_hourly: false,
    })
    expect(screen.getByText('2%')).toBeTruthy()
    expect(screen.getByText('858.5 MWh')).toBeTruthy()
    expect(screen.getByText('12,345,678')).toBeTruthy()
    expect(screen.getByText('17.89')).toBeTruthy()
    expect(screen.getByText(/does not establish site feasibility/)).toBeTruthy()
    await user.click(screen.getByText('Model assumptions'))
    expect(screen.getByText('Test resource profiles are synthetic.')).toBeTruthy()
    await user.clear(solar)
    await user.type(solar, '346')
    expect(screen.queryByRole('heading', { name: 'Modeled reliability target met' })).toBeNull()
  })

  it('shows a backend error and allows a successful retry', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(new Response(JSON.stringify({ error: { message: 'The selected resource dataset is unavailable.' } }), { status: 503 }))
      .mockResolvedValueOnce(response())
    vi.stubGlobal('fetch', fetchMock)
    render(<PlanningPanel location={location} onClose={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: 'Evaluate configuration' }))
    expect((await screen.findByRole('alert')).textContent).toContain('The selected resource dataset is unavailable.')
    expect(screen.queryByRole('heading', { name: 'Modeled reliability target met' })).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Retry evaluation' }))
    await screen.findByRole('heading', { name: 'Modeled reliability target met' })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('prevents an invalid zero-demand submission', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn<typeof fetch>()
    vi.stubGlobal('fetch', fetchMock)
    render(<PlanningPanel location={location} onClose={vi.fn()} />)
    const demand = screen.getByRole('spinbutton', { name: 'Electricity demand (kW)' })
    await user.clear(demand)
    await user.type(demand, '0')
    await user.click(screen.getByRole('button', { name: 'Evaluate configuration' }))
    expect((demand as HTMLInputElement).checkValidity()).toBe(false)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('aborts an in-flight request when the user closes the panel', async () => {
    const user = userEvent.setup()
    let signal: AbortSignal | null | undefined
    vi.stubGlobal('fetch', vi.fn<typeof fetch>().mockImplementation((_url, options) => {
      signal = options?.signal
      return new Promise((_resolve, reject) => {
        signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true })
      })
    }))
    function Harness() {
      const [open, setOpen] = useState(true)
      return open ? <PlanningPanel location={location} onClose={() => setOpen(false)} /> : <p>Planner closed</p>
    }
    render(<Harness />)
    await user.click(screen.getByRole('button', { name: 'Evaluate configuration' }))
    expect((screen.getByRole('spinbutton', { name: 'Electricity demand (kW)' }) as HTMLInputElement).disabled).toBe(true)
    expect(screen.getByRole('button', { name: 'Evaluating configuration…' })).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Close energy planner' }))
    await waitFor(() => expect(signal?.aborted).toBe(true))
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(screen.getByText('Planner closed')).toBeTruthy()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('delegates native Escape cancellation to the parent close handler', () => {
    const onClose = vi.fn()
    render(<PlanningPanel location={location} onClose={onClose} />)
    const event = new Event('cancel', { cancelable: true })
    fireEvent(screen.getByRole('dialog'), event)
    expect(event.defaultPrevented).toBe(true)
    expect(onClose).toHaveBeenCalledOnce()
  })
})
