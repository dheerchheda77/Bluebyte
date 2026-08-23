import React, { useState } from 'react'
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ArrowDownRightIcon, ArrowUpRightIcon, DatabaseIcon } from 'lucide-react'
import { datasetSources, ednaDetections } from '../data/marineContent'
import { ednaSites } from '../data/zones'
import { correlationPairs } from '../utils/series'
import type { Station } from '../types/marine'
import { StationDetail } from './StationDetail'

type TabId = 'signals' | 'genetics' | 'sources'

const TABS: { id: TabId; label: string }[] = [
  { id: 'signals', label: 'Signals' },
  { id: 'genetics', label: 'Genetics' },
  { id: 'sources', label: 'Sources' },
]

interface InsightPanelProps {
  station: Station | null
  species: any[]
  onClearStation: () => void
}

export function InsightPanel({ station, species, onClearStation }: InsightPanelProps) {
  const [tab, setTab] = useState<TabId>('signals')

  if (station) {
    return <StationDetail station={station} onBack={onClearStation} />
  }

  return (
    <aside
      className="flex w-[360px] shrink-0 flex-col border-l border-line bg-abyss-900"
      aria-label="Cross-domain insights"
    >
      <div className="flex shrink-0 gap-1 border-b border-line px-3 pt-3">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            aria-current={tab === t.id}
            className={`relative px-3 pb-2.5 text-xs font-medium transition-colors duration-150 ${
              tab === t.id ? 'text-foam' : 'text-foam-dim hover:text-foam-muted'
            }`}
          >
            {t.label}
            {tab === t.id && (
              <span className="absolute inset-x-0 -bottom-px h-0.5 rounded-full bg-tide" />
            )}
          </button>
        ))}
      </div>

      <div className="bb-scroll flex-1 overflow-y-auto">
        {tab === 'signals' && <SignalsTab species={species} />}
        {tab === 'genetics' && <GeneticsTab />}
        {tab === 'sources' && <SourcesTab />}
      </div>
    </aside>
  )
}

function SignalsTab({ species }: { species: any[] }) {
  return (
    <>
      <section className="border-b border-line-soft px-4 py-4">
        <div className="flex items-baseline justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-foam">
            SST × eDNA richness
          </h3>
          <span className="font-mono text-2xs text-bio">r = 0.71</span>
        </div>
        <p className="mt-1 text-2xs leading-relaxed text-foam-muted">
          Warmer surface water tracks higher detected taxa richness across 24 paired samples in the
          selected window.
        </p>
        <div className="mt-3 h-40">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 4, right: 8, bottom: 4, left: -18 }}>
              <CartesianGrid stroke="#132b3c" />
              <XAxis
                type="number"
                dataKey="sst"
                domain={[28, 31]}
                tick={{ fill: '#5f8298', fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: '#1a3c53' }}
                unit="°"
              />
              <YAxis
                type="number"
                dataKey="richness"
                domain={[170, 250]}
                tick={{ fill: '#5f8298', fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: '#1a3c53' }}
              />
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
              <Scatter data={correlationPairs} fill="#37c8e0" fillOpacity={0.75} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="px-4 py-4">
        <h3 className="pb-2 text-xs font-semibold uppercase tracking-wider text-foam">
          Species distribution forecast
        </h3>
        <ul className="space-y-2">
          {species.map((s) => {
            const up = s.trend >= 0
            return (
              <li
                key={s.id}
                className="rounded-md border border-line-soft bg-abyss-800 px-3 py-2.5"
              >
                <div className="flex items-baseline gap-2">
                  <span className="truncate text-xs font-medium text-foam">{s.common}</span>
                  <span
                    className={`ml-auto flex shrink-0 items-center gap-0.5 font-mono text-2xs ${
                      up ? 'text-bio' : 'text-risk'
                    }`}
                  >
                    {up ? (
                      <ArrowUpRightIcon className="h-3 w-3" aria-hidden="true" />
                    ) : (
                      <ArrowDownRightIcon className="h-3 w-3" aria-hidden="true" />
                    )}
                    {Math.abs(s.trend).toFixed(1)}%
                  </span>
                </div>
                <p className="truncate font-mono text-2xs italic text-foam-dim">{s.scientific}</p>
                <div className="mt-2 flex items-center gap-2">
                  <div
                    className="h-1 flex-1 overflow-hidden rounded-full bg-abyss-700"
                    role="img"
                    aria-label={`Model confidence ${Math.round(s.confidence * 100)} percent`}
                  >
                    <div
                      className="h-full rounded-full bg-tide"
                      style={{ width: `${s.confidence * 100}%` }}
                    />
                  </div>
                  <span className="font-mono text-2xs tabular-nums text-foam-muted">
                    {Math.round(s.confidence * 100)}%
                  </span>
                </div>
                <p className="mt-1.5 text-2xs text-foam-muted">Driver: {s.driver}</p>
              </li>
            )
          })}
        </ul>
      </section>
    </>
  )
}

function GeneticsTab() {
  const statusStyle: Record<string, string> = {
    known: 'bg-abyss-700 text-foam-muted',
    novel: 'bg-[#a78bfa]/15 text-[#c4b1fd]',
    invasive: 'bg-risk/15 text-risk',
  }

  return (
    <>
      <section className="grid grid-cols-3 divide-x divide-line-soft border-b border-line-soft">
        {[
          { label: 'Sites', value: ednaSites.length },
          {
            label: 'Taxa',
            value: ednaSites.reduce((sum, s) => sum + s.richness, 0),
          },
          {
            label: 'Unassigned',
            value: ednaSites.reduce((sum, s) => sum + s.novelTaxa, 0),
          },
        ].map((stat) => (
          <div key={stat.label} className="px-4 py-3">
            <p className="font-mono text-lg tabular-nums text-foam">{stat.value}</p>
            <p className="font-mono text-2xs uppercase tracking-wider text-foam-dim">
              {stat.label}
            </p>
          </div>
        ))}
      </section>

      <section className="px-4 py-4">
        <h3 className="pb-2 text-xs font-semibold uppercase tracking-wider text-foam">
          Top eDNA detections
        </h3>
        <ul className="space-y-2">
          {ednaDetections.map((d) => (
            <li key={d.id} className="rounded-md border border-line-soft bg-abyss-800 px-3 py-2.5">
              <div className="flex items-center gap-2">
                <span className="truncate text-xs text-foam">{d.taxon}</span>
                <span
                  className={`ml-auto shrink-0 rounded px-1.5 py-0.5 font-mono text-2xs uppercase ${statusStyle[d.status]}`}
                >
                  {d.status}
                </span>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <div className="h-1 flex-1 overflow-hidden rounded-full bg-abyss-700">
                  <div
                    className="h-full rounded-full bg-[#a78bfa]"
                    style={{ width: `${Math.min(100, d.readShare * 320)}%` }}
                  />
                </div>
                <span className="font-mono text-2xs tabular-nums text-foam-muted">
                  {(d.readShare * 100).toFixed(1)}%
                </span>
              </div>
              <p className="mt-1.5 font-mono text-2xs text-foam-dim">
                {d.siteId} · {d.barcode}
              </p>
            </li>
          ))}
        </ul>
      </section>
    </>
  )
}

function SourcesTab() {
  const statusStyle: Record<string, string> = {
    streaming: 'text-bio',
    harmonized: 'text-tide',
    stale: 'text-catch',
  }

  return (
    <section className="px-4 py-4">
      <div className="flex items-center gap-2 pb-1">
        <DatabaseIcon className="h-3.5 w-3.5 text-foam-muted" aria-hidden="true" />
        <h3 className="text-xs font-semibold uppercase tracking-wider text-foam">Provenance</h3>
      </div>
      <p className="pb-3 text-2xs leading-relaxed text-foam-muted">
        Every figure on this console resolves to one of these harmonized feeds. Quality is the share
        of records passing schema and range validation.
      </p>
      <ul className="divide-y divide-line-soft">
        {datasetSources.map((s) => (
          <li key={s.id} className="py-2.5">
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-2xs uppercase tracking-wider text-tide">
                {s.agency}
              </span>
              <span className={`ml-auto font-mono text-2xs ${statusStyle[s.status]}`}>
                {s.status}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-foam">{s.dataset}</p>
            <div className="mt-1.5 flex items-center gap-3 font-mono text-2xs text-foam-dim">
              <span>{s.records} rows</span>
              <span>· {s.latency} lag</span>
              <span className="ml-auto text-foam-muted">
                {Math.round(s.quality * 100)}% clean
              </span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
