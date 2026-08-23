import React, { useState } from 'react'
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ChevronDownIcon } from 'lucide-react'
import { series } from '../utils/series'

const CHARTS: {
  key: 'sst' | 'salinity' | 'oxygen' | 'chlorophyll'
  label: string
  unit: string
  color: string
  domain: [number, number]
}[] = [
  { key: 'sst', label: 'Sea surface temperature', unit: '°C', color: '#37c8e0', domain: [27.5, 30.5] },
  { key: 'salinity', label: 'Salinity', unit: 'PSU', color: '#8fadbe', domain: [34, 35.4] },
  { key: 'oxygen', label: 'Dissolved oxygen', unit: 'mg/L', color: '#f2624a', domain: [2.8, 4.8] },
  { key: 'chlorophyll', label: 'Chlorophyll-a', unit: 'mg/m³', color: '#56d9a3', domain: [0.6, 2.6] },
]

interface TimeSeriesStripProps {
  timeWindow: string
}

export function TimeSeriesStrip({ timeWindow }: TimeSeriesStripProps) {
  const [open, setOpen] = useState(true)
  const first = series[0]
  const last = series[series.length - 1]

  return (
    <section
      className="shrink-0 border-t border-line bg-abyss-900"
      aria-label="Environmental time series"
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-4 py-2 text-left transition-colors duration-150 hover:bg-abyss-800"
      >
        <h2 className="text-xs font-semibold uppercase tracking-wider text-foam">
          Environmental drivers
        </h2>
        <span className="font-mono text-2xs text-foam-dim">{timeWindow} · hourly · 5 stations</span>
        <ChevronDownIcon
          aria-hidden="true"
          className={`ml-auto h-4 w-4 text-foam-dim transition-transform duration-200 ${
            open ? '' : '-rotate-90'
          }`}
        />
      </button>

      {open && (
        <div className="grid grid-cols-2 gap-px border-t border-line-soft bg-line-soft xl:grid-cols-4">
          {CHARTS.map((chart) => {
            const delta = (last[chart.key] as number) - (first[chart.key] as number)
            const rising = delta >= 0
            return (
              <article key={chart.key} className="bg-abyss-900 px-4 pb-2 pt-2.5">
                <div className="flex items-baseline gap-2">
                  <h3 className="truncate text-2xs uppercase tracking-wider text-foam-muted">
                    {chart.label}
                  </h3>
                  <span
                    className={`ml-auto shrink-0 font-mono text-2xs ${
                      rising ? 'text-bio' : 'text-catch'
                    }`}
                  >
                    {rising ? '+' : ''}
                    {delta.toFixed(2)}
                  </span>
                </div>
                <p className="font-mono text-lg tabular-nums leading-tight text-foam">
                  {(last[chart.key] as number).toFixed(2)}
                  <span className="ml-1 text-2xs text-foam-dim">{chart.unit}</span>
                </p>
                <div className="mt-1 h-[68px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={series} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
                      <defs>
                        <linearGradient id={`fill-${chart.key}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor={chart.color} stopOpacity={0.3} />
                          <stop offset="100%" stopColor={chart.color} stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="t" hide />
                      <YAxis hide domain={chart.domain} />
                      <Tooltip
                        cursor={{ stroke: '#1a3c53' }}
                        contentStyle={{
                          background: '#0b2434',
                          border: '1px solid #1a3c53',
                          borderRadius: 6,
                          fontSize: 11,
                        }}
                        labelStyle={{ color: '#8fadbe' }}
                      />
                      <Area
                        type="monotone"
                        dataKey={chart.key}
                        stroke={chart.color}
                        strokeWidth={1.5}
                        fill={`url(#fill-${chart.key})`}
                        isAnimationActive={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
