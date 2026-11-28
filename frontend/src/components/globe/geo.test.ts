import { describe, expect, it } from 'vitest'
import { geographicPosition, graticulePositions, isSurfaceVisible } from './geo'
import { coordinateLabel } from '../../data/coordinates'
import { findLocations } from '../../data/locations'

describe('geographic alignment with the equirectangular Earth map', () => {
  it.each([
    [0, 0, [1, 0, 0]], [0, 90, [0, 0, -1]],
    [0, -90, [0, 0, 1]], [90, 20, [0, 1, 0]], [-90, 30, [0, -1, 0]],
  ])('places latitude %s longitude %s on the expected axis', (lat, lon, expected) => {
    const actual = geographicPosition(lat, lon).toArray()
    expected.forEach((value, index) => expect(actual[index]).toBeCloseTo(value, 10))
  })
  it('preserves a point’s latitude and longitude on a scaled sphere', () => {
    const point = geographicPosition(10.57, 72.64, 1.8)
    expect(point.length()).toBeCloseTo(1.8, 10)
    expect(Math.asin(point.y / 1.8) * 180 / Math.PI).toBeCloseTo(10.57, 8)
    expect(Math.atan2(-point.z, point.x) * 180 / Math.PI).toBeCloseTo(72.64, 8)
  })
  it('rejects impossible or non-finite positions', () => {
    expect(() => geographicPosition(91, 0)).toThrow()
    expect(() => geographicPosition(0, NaN)).toThrow()
    expect(() => geographicPosition(0, 0, -1)).toThrow()
  })
  it('rejects back-side and occluded near-horizon markers for both display and picking', () => {
    const camera = geographicPosition(0, 0, 5)
    expect(isSurfaceVisible(geographicPosition(0, 0), camera, 1)).toBe(true)
    expect(isSurfaceVisible(geographicPosition(0, 180), camera, 1)).toBe(false)
    expect(isSurfaceVisible(geographicPosition(0, 85), camera, 1)).toBe(false)
    expect(isSurfaceVisible(geographicPosition(0, 60), camera, 1)).toBe(true)
  })
  it('keeps all geographic grid vertices on the same sphere', () => {
    const points = graticulePositions(1.806)
    for (let index = 0; index < points.length; index += 3) {
      expect(Math.hypot(points[index], points[index + 1], points[index + 2])).toBeCloseTo(1.806, 6)
    }
  })
  it('labels hemispheres consistently', () => {
    expect(coordinateLabel(-4.49, 'longitude')).toBe('4.49° W')
    expect(coordinateLabel(10.57, 'latitude')).toBe('10.57° N')
  })
  it('searches supported place names, countries, and regions', () => {
    expect(findLocations('  FRANCE ')).toHaveLength(1)
    expect(findLocations('france')[0].id).toBe('brest')
    expect(findLocations('Arabian')[0].id).toBe('lakshadweep')
    expect(findLocations('Tokyo')).toHaveLength(0)
  })
})
