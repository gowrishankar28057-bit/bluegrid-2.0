import { Vector3 } from 'three'

/** Three.js SphereGeometry coordinates for an equirectangular map, north at top. */
export function geographicPosition(latitude: number, longitude: number, radius = 1) {
  if (![latitude, longitude, radius].every(Number.isFinite) || Math.abs(latitude) > 90 || radius <= 0) {
    throw new Error('Invalid geographic position')
  }
  const lat = latitude * Math.PI / 180
  const lon = longitude * Math.PI / 180
  return new Vector3(radius * Math.cos(lat) * Math.cos(lon), radius * Math.sin(lat), -radius * Math.cos(lat) * Math.sin(lon))
}

/** Tangent-plane visibility also gates picking, preventing clicks through Earth. */
export function isSurfaceVisible(position: Vector3, camera: Vector3, sphereRadius: number) {
  return position.dot(camera) > sphereRadius * position.length()
}

export function graticulePositions(radius: number) {
  const positions: number[] = []
  const segment = (lat1: number, lon1: number, lat2: number, lon2: number) => {
    positions.push(...geographicPosition(lat1, lon1, radius).toArray(), ...geographicPosition(lat2, lon2, radius).toArray())
  }
  for (let lat = -60; lat <= 60; lat += 30) {
    for (let lon = -180; lon < 180; lon += 3) segment(lat, lon, lat, lon + 3)
  }
  for (let lon = -180; lon < 180; lon += 30) {
    for (let lat = -90; lat < 90; lat += 3) segment(lat, lon, lat + 3, lon)
  }
  return new Float32Array(positions)
}
