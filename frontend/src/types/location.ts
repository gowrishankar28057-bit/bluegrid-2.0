export type LocationId = 'lakshadweep' | 'brest'

export interface Location {
  id: LocationId
  name: string
  country: string
  region: string
  latitude: number
  longitude: number
  description: string
  technologies: string[]
  timezone: string
}
