import type { Location } from '../types/location'

/** Demonstration scope only: these labels do not establish site feasibility. */
export const LAKSHADWEEP: Location = {
  id: 'lakshadweep',
  name: 'Lakshadweep',
  country: 'India',
  region: 'Arabian Sea',
  latitude: 10.57,
  longitude: 72.64,
  description:
    'An island-system demonstration in the Arabian Sea. Explore land and ocean energy concepts; technology labels describe demo scope, not verified resource availability or feasibility.',
  technologies: [
    'Floating solar · demo',
    'Onshore solar · demo',
    'Onshore wind · demo',
    'Offshore wind · demo',
    'OTEC · demo',
    'Wave energy · demo',
    'Battery storage · demo',
  ],
  timezone: 'Asia/Kolkata',
}

export const BREST: Location = {
  id: 'brest',
  name: 'Brest',
  country: 'France',
  region: 'Brittany, Atlantic Coast',
  latitude: 48.39,
  longitude: -4.49,
  description:
    'A coastal-system demonstration in Brittany. Explore land and marine energy concepts; technology labels describe demo scope, not verified resource availability or feasibility.',
  technologies: [
    'Floating solar · demo',
    'Onshore solar · demo',
    'Onshore wind · demo',
    'Offshore wind · demo',
    'Wave energy · demo',
    'Battery storage · demo',
  ],
  timezone: 'Europe/Paris',
}

export const DEMO_LOCATIONS: readonly Location[] = [LAKSHADWEEP, BREST]

export default LAKSHADWEEP

function normalizeQuery(value: string): string {
  return value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase()
}

/** Empty queries return both demos; search includes place, country, and region. */
export function findLocations(query: string): Location[] {
  const normalized = normalizeQuery(query)
  return DEMO_LOCATIONS.filter((location) =>
    [location.name, location.country, location.region].some((value) =>
      normalizeQuery(value).includes(normalized),
    ),
  )
}
