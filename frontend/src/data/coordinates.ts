export function coordinateLabel(value: number, axis: 'latitude' | 'longitude') {
  const suffix = axis === 'latitude' ? (value >= 0 ? 'N' : 'S') : (value >= 0 ? 'E' : 'W')
  return `${Math.abs(value).toFixed(2)}° ${suffix}`
}
