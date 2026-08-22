import React from 'react'
import { LayersIcon, MapIcon } from 'lucide-react'
import type { DomainId, LayerId } from '../types/marine'
import { layers } from '../data/marineContent'
import { AlertsFeed } from './AlertsFeed'

const DOMAIN_LABEL: Record<DomainId, string> = {
  ocean: 'Oceanography',
  fisheries: 'Fisheries',
  biodiversity: 'Molecular biodiversity',
}

const BASEMAPS: { id: 'bathymetric' | 'satellite' | 'minimal'; label: string }[] = [
  { id: 'bathymetric', label: 'Bathy' },
  { id: 'satellite', label: 'Satellite' },
  { id: 'minimal', label: 'Minimal' },
]

interface LayerRailProps {
  activeLayers: Record<LayerId, boolean>
  onToggleLayer: (id: LayerId) => void
  basemap: 'bathymetric' | 'satellite' | 'minimal'
  onBasemapChange: (id: 'bathymetric' | 'satellite' | 'minimal') => void
  dense: boolean
  alerts: any[]
}

export function LayerRail({
  activeLayers,
  onToggleLayer,
  basemap,
  onBasemapChange,
  dense,
  alerts,
}: LayerRailProps) {
  const domains: DomainId[] = ['ocean', 'fisheries', 'biodiversity']
  const activeCount = Object.values(activeLayers).filter(Boolean).length

  return (
    <aside
      className="flex w-[280px] shrink-0 flex-col border-r border-line bg-abyss-900"
      aria-label="Map layers and alerts"
    >
      <div className="flex items-center gap-2 border-b border-line px-4 py-3">
        <LayersIcon className="h-4 w-4 text-foam-muted" aria-hidden="true" />
        <h2 className="text-xs font-semibold uppercase tracking-wider text-foam">Layers</h2>
        <span className="ml-auto font-mono text-2xs text-foam-dim">{activeCount}/7 on</span>
      </div>

      <div className={`bb-scroll flex-1 overflow-y-auto ${dense ? 'py-1' : 'py-2'}`}>
        {domains.map((domain) => (
          <section key={domain} className="px-3 pb-2">
            <h3 className="px-1 pb-1 pt-2 font-mono text-2xs uppercase tracking-[0.14em] text-foam-dim">
              {DOMAIN_LABEL[domain]}
            </h3>
            <ul>
              {layers
                .filter((layer) => layer.domain === domain)
                .map((layer) => {
                  const on = activeLayers[layer.id]
                  return (
                    <li key={layer.id}>
                      <button
                        type="button"
                        onClick={() => onToggleLayer(layer.id)}
                        aria-pressed={on}
                        className={`group flex w-full items-start gap-2.5 rounded-md px-2 text-left transition-colors duration-150 hover:bg-abyss-800 ${
                          dense ? 'py-1.5' : 'py-2'
                        }`}
                      >
                        <span
                          aria-hidden="true"
                          className="mt-1 h-2.5 w-2.5 shrink-0 rounded-sm border transition-colors duration-150"
                          style={{
                            borderColor: on ? layer.color : '#2a4c63',
                            backgroundColor: on ? layer.color : 'transparent',
                          }}
                        />
                        <span className="min-w-0 flex-1">
                          <span
                            className={`block truncate text-xs ${on ? 'text-foam' : 'text-foam-muted'}`}
                          >
                            {layer.label}
                          </span>
                          {!dense && (
                            <span className="block truncate font-mono text-2xs text-foam-dim">
                              {layer.detail}
                            </span>
                          )}
                        </span>
                      </button>
                    </li>
                  )
                })}
            </ul>
          </section>
        ))}

        <section className="border-t border-line-soft px-4 py-3">
          <div className="flex items-center gap-2 pb-2">
            <MapIcon className="h-3.5 w-3.5 text-foam-dim" aria-hidden="true" />
            <h3 className="font-mono text-2xs uppercase tracking-[0.14em] text-foam-dim">
              Basemap
            </h3>
          </div>
          <div className="grid grid-cols-3 gap-1 rounded-md border border-line bg-abyss-800 p-0.5">
            {BASEMAPS.map((b) => (
              <button
                key={b.id}
                type="button"
                onClick={() => onBasemapChange(b.id)}
                aria-pressed={basemap === b.id}
                className={`rounded py-1 text-2xs font-medium transition-colors duration-150 ${
                  basemap === b.id
                    ? 'bg-abyss-600 text-foam'
                    : 'text-foam-muted hover:bg-abyss-700 hover:text-foam'
                }`}
              >
                {b.label}
              </button>
            ))}
          </div>
        </section>
      </div>

      <AlertsFeed dense={dense} alerts={alerts} />
    </aside>
  )
}
