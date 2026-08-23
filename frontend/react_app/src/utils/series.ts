import type { SeriesPoint } from '../types/marine'

/** Deterministic pseudo-random so the console renders identically on every load. */
function noise(seed: number): number {
  const x = Math.sin(seed * 127.1) * 43758.5453
  return x - Math.floor(x)
}

/** 48 hourly observations ending "now", shaped like a diurnal ocean signal. */
export function buildSeries(): SeriesPoint[] {
  const points: SeriesPoint[] = []
  for (let i = 47; i >= 0; i--) {
    const hour = (24 - (i % 24)) % 24
    const diurnal = Math.sin(((hour - 6) / 24) * Math.PI * 2)
    const drift = (47 - i) / 47
    points.push({
      t: `${String(hour).padStart(2, '0')}:00`,
      sst: Number((28.6 + diurnal * 0.7 + drift * 0.9 + noise(i) * 0.16).toFixed(2)),
      salinity: Number((34.8 - drift * 0.4 + noise(i + 90) * 0.12).toFixed(2)),
      oxygen: Number((4.3 - drift * 1.1 - Math.max(0, diurnal) * 0.2 + noise(i + 12) * 0.08).toFixed(2)),
      chlorophyll: Number((0.9 + drift * 1.4 + noise(i + 41) * 0.12).toFixed(2)),
      richness: Math.round(180 + drift * 46 + noise(i + 7) * 14),
    })
  }
  return points
}

export const series = buildSeries()

export const correlationPairs = series
  .filter((_, i) => i % 2 === 0)
  .map((p) => ({ sst: p.sst, richness: p.richness, chlorophyll: p.chlorophyll }))

/** Colour ramp for the SST field, cool → warm. */
export function sstColor(value: number): string {
  const stops: [number, string][] = [
    [26.5, '#2b6cb0'],
    [27.5, '#2f9ec4'],
    [28.5, '#39c1a5'],
    [29.3, '#d8c04a'],
    [30.0, '#e8863f'],
    [31.0, '#e0503c'],
  ]
  for (const [limit, color] of stops) {
    if (value <= limit) return color
  }
  return '#c8352f'
}
