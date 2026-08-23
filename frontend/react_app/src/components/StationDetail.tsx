import React from 'react'
import { ArrowLeftIcon, CircleAlertIcon } from 'lucide-react'
import { Area, AreaChart, ResponsiveContainer, YAxis } from 'recharts'
import type { Station } from '../types/marine'
import { series } from '../utils/series'

interface StationDetailProps {
  station: Station
  onBack: () => void
}

export function StationDetail({ station, onBack }: StationDetailProps) {
  const readings: { label: string; value: string; unit: string; warn?: boolean }[] = [
    { label: 'SST', value: station.sst.toFixed(1), unit: '°C' },
    { label: 'Salinity', value: station.salinity.toFixed(1), unit: 'PSU' },
    {
      label: 'Dissolved O₂',
      value: station.oxygen.toFixed(1),
      unit: 'mg/L',
      warn: station.oxygen < 3.5,
    },
    { label: 'Chl-a', value: station.chlorophyll.toFixed(2), unit: 'mg/m³' },
  ]

  return (
    <aside
      className="flex w-[360px] shrink-0 flex-col border-l border-line bg-abyss-900"
      aria-label={`Station ${station.name}`}
    >
      <div className="flex shrink-0 items-center gap-2 border-b border-line px-3 py-3">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-foam-muted transition-colors duration-150 hover:bg-abyss-800 hover:text-foam"
        >
          <ArrowLeftIcon className="h-3.5 w-3.5" aria-hidden="true" />
          Insights
        </button>
        <span className="ml-auto font-mono text-2xs uppercase tracking-wider text-foam-dim">
          {station.id}
        </span>
      </div>

      <div className="bb-scroll flex-1 overflow-y-auto">
        <header className="border-b border-line-soft px-4 py-4">
          <h2 className="text-sm font-semibold leading-tight text-foam">{station.name}</h2>
          <p className="mt-1 font-mono text-2xs text-foam-dim">
            {station.agency} · {station.lat.toFixed(2)}°N {station.lng.toFixed(2)}°E ·{' '}
            {station.depth} m
          </p>
          {station.status === 'anomaly' && (
            <p className="mt-3 flex items-start gap-2 rounded-md border border-risk/30 bg-risk/10 px-2.5 py-2 text-2xs leading-relaxed text-[#ffb3a6]">
              <CircleAlertIcon className="mt-px h-3.5 w-3.5 shrink-0 text-risk" aria-hidden="true" />
              Anomaly ensemble flagged this station — readings deviate more than 2σ from the
              seasonal baseline.
            </p>
          )}
          {station.status === 'offline' && (
            <p className="mt-3 rounded-md border border-line bg-abyss-800 px-2.5 py-2 text-2xs leading-relaxed text-foam-muted">
              No telemetry for {Math.round(station.updatedMinutes / 60)} h. Values below are the last
              known transmission.
            </p>
          )}
        </header>

        <section className="grid grid-cols-2 gap-px border-b border-line-soft bg-line-soft">
          {readings.map((r) => (
            <div key={r.label} className="bg-abyss-900 px-4 py-3">
              <p className="font-mono text-2xs uppercase tracking-wider text-foam-dim">{r.label}</p>
              <p
                className={`font-mono text-xl tabular-nums ${r.warn ? 'text-risk' : 'text-foam'}`}
              >
                {r.value}
                <span className="ml-1 text-2xs text-foam-dim">{r.unit}</span>
              </p>
            </div>
          ))}
        </section>

        <section className="px-4 py-4">
          <h3 className="pb-2 text-xs font-semibold uppercase tracking-wider text-foam">
            Dissolved oxygen · 48 h
          </h3>
          <div className="h-28">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={series} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="do-fill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f2624a" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#f2624a" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <YAxis hide domain={[2.5, 5]} />
                <Area
                  type="monotone"
                  dataKey="oxygen"
                  stroke="#f2624a"
                  strokeWidth={1.5}
                  fill="url(#do-fill)"
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-2xs leading-relaxed text-foam-muted">
            Declining 1.1 mg/L over the window. Sustained values below 3.5 mg/L correlate with
            demersal catch collapse in this shelf segment.
          </p>
        </section>

        <section className="border-t border-line-soft px-4 py-4">
          <h3 className="pb-2 text-xs font-semibold uppercase tracking-wider text-foam">
            Linked records
          </h3>
          <ul className="space-y-1.5 font-mono text-2xs text-foam-muted">
            <li className="flex justify-between">
              <span>Catch surveys within 50 km</span>
              <span className="text-foam">37</span>
            </li>
            <li className="flex justify-between">
              <span>eDNA samples within 50 km</span>
              <span className="text-foam">4</span>
            </li>
            <li className="flex justify-between">
              <span>Vessel transits (24 h)</span>
              <span className="text-foam">112</span>
            </li>
            <li className="flex justify-between">
              <span>Last QC pass</span>
              <span className="text-foam">{station.updatedMinutes} min ago</span>
            </li>
          </ul>
        </section>
      </div>
    </aside>
  )
}
