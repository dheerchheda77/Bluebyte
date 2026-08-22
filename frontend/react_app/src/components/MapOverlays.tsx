import React from 'react'
import { MousePointerClickIcon } from 'lucide-react'
import type { LayerId } from '../types/marine'
import { layers } from '../data/marineContent'

const RAMP = ['#2b6cb0', '#2f9ec4', '#39c1a5', '#d8c04a', '#e8863f', '#e0503c']

interface MapOverlaysProps {
  activeLayers: Record<LayerId, boolean>
  anomalyCount: number
  hasSelection: boolean
}

export function MapOverlays({ activeLayers, anomalyCount, hasSelection }: MapOverlaysProps) {
  const activeKeys = layers.filter((l) => activeLayers[l.id] && l.id !== 'sst')

  return (
    <>
      <div className="pointer-events-none absolute left-4 top-4 z-[500] flex items-center gap-3 rounded-md border border-line bg-abyss-900/90 px-3 py-2 backdrop-blur">
        <div>
          <p className="text-xs font-semibold text-foam">Indian EEZ</p>
          <p className="font-mono text-2xs text-foam-dim">2.02 M km² · 5 basins</p>
        </div>
        <span className="h-6 w-px bg-line" aria-hidden="true" />
        <p className="font-mono text-2xs text-risk">{anomalyCount} anomalies</p>
      </div>

      {!hasSelection && (
        <div className="pointer-events-none absolute left-1/2 top-4 z-[500] hidden -translate-x-1/2 items-center gap-1.5 rounded-full border border-line bg-abyss-900/90 px-3 py-1.5 font-mono text-2xs text-foam-muted backdrop-blur md:flex">
          <MousePointerClickIcon className="h-3 w-3" aria-hidden="true" />
          Select a buoy to inspect its cross-domain record
        </div>
      )}

      <div className="pointer-events-none absolute bottom-4 left-4 z-[500] rounded-md border border-line bg-abyss-900/90 px-3 py-2.5 backdrop-blur">
        {activeLayers.sst && (
          <div className="pb-2">
            <p className="pb-1 font-mono text-2xs uppercase tracking-wider text-foam-dim">
              SST °C
            </p>
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-2xs text-foam-muted">26</span>
              <div className="flex h-1.5 w-28 overflow-hidden rounded-full">
                {RAMP.map((c) => (
                  <span key={c} className="h-full flex-1" style={{ backgroundColor: c }} />
                ))}
              </div>
              <span className="font-mono text-2xs text-foam-muted">31</span>
            </div>
          </div>
        )}
        <ul className="space-y-1">
          {activeKeys.map((l) => (
            <li key={l.id} className="flex items-center gap-2">
              <span
                aria-hidden="true"
                className="h-1.5 w-1.5 rounded-full"
                style={{ backgroundColor: l.color }}
              />
              <span className="text-2xs text-foam-muted">{l.label}</span>
            </li>
          ))}
          {activeKeys.length === 0 && !activeLayers.sst && (
            <li className="text-2xs text-foam-dim">No layers active</li>
          )}
        </ul>
      </div>
    </>
  )
}
