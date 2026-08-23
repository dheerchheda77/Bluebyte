/**
 * Deterministic synthetic SST / chlorophyll field over the Indian EEZ.
 * Derived data — generated rather than stored so the grid stays adjustable.
 */
export interface FieldCell {
  lat: number
  lng: number
  sst: number
  chlorophyll: number
}

function hash(x: number, y: number): number {
  const n = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453
  return n - Math.floor(n)
}

export function buildField(): FieldCell[] {
  const cells: FieldCell[] = []
  for (let lat = 6; lat <= 23; lat += 1.1) {
    for (let lng = 66; lng <= 94; lng += 1.1) {
      // Skip the landmass wedge so the field reads as ocean only.
      const onLand =
        lng > 70.5 && lng < 88 && lat > 8.4 && lat < 23 && !isCoastalWater(lat, lng)
      if (onLand) continue
      const warmth = 31.2 - Math.abs(lat - 12) * 0.22 + hash(lat, lng) * 0.9
      const coastal = Math.max(0, 2.6 - Math.abs(distanceToCoast(lat, lng)) * 0.9)
      cells.push({
        lat: Number(lat.toFixed(2)),
        lng: Number(lng.toFixed(2)),
        sst: Number(warmth.toFixed(2)),
        chlorophyll: Number((0.18 + coastal * hash(lng, lat)).toFixed(2)),
      })
    }
  }
  return cells
}

function isCoastalWater(lat: number, lng: number): boolean {
  // Rough west/east coast bands plus the southern tip.
  const westCoast = 73.2 + (lat - 8) * 0.28
  const eastCoast = 80.4 + (lat - 8) * 0.42
  return lng < westCoast - 0.6 || lng > eastCoast + 0.6 || lat < 8.6
}

function distanceToCoast(lat: number, lng: number): number {
  const westCoast = 73.2 + (lat - 8) * 0.28
  const eastCoast = 80.4 + (lat - 8) * 0.42
  return Math.min(Math.abs(lng - westCoast), Math.abs(lng - eastCoast))
}

export const oceanField = buildField()
