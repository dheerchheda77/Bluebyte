import React, { useState } from 'react'
import { ChevronDownIcon, TriangleAlertIcon } from 'lucide-react'
import type { MarineAlert } from '../types/marine'

const SEVERITY: Record<string, { dot: string; label: string }> = {
  critical: { dot: 'bg-risk', label: 'text-risk' },
  warning: { dot: 'bg-catch', label: 'text-catch' },
  info: { dot: 'bg-tide', label: 'text-tide' },
}

interface AlertsFeedProps {
  dense: boolean
  alerts: MarineAlert[]
}

export function AlertsFeed({ dense, alerts }: AlertsFeedProps) {
  const [open, setOpen] = useState(true)
  const critical = alerts.filter((a) => a.severity === 'critical').length

  return (
    <section className="shrink-0 border-t border-line bg-abyss-900" aria-label="Active alerts">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-4 py-3 text-left transition-colors duration-150 hover:bg-abyss-800"
      >
        <TriangleAlertIcon className="h-4 w-4 text-catch" aria-hidden="true" />
        <h2 className="text-xs font-semibold uppercase tracking-wider text-foam">Alerts</h2>
        {critical > 0 && (
          <span className="rounded bg-risk/15 px-1.5 py-0.5 font-mono text-2xs text-risk">
            {critical} critical
          </span>
        )}
        <ChevronDownIcon
          aria-hidden="true"
          className={`ml-auto h-4 w-4 text-foam-dim transition-transform duration-200 ${
            open ? '' : '-rotate-90'
          }`}
        />
      </button>

      {open && (
        <ul className={`bb-scroll max-h-56 overflow-y-auto px-3 pb-3 ${dense ? 'space-y-1' : 'space-y-1.5'}`}>
          {alerts.map((alert) => (
            <li
              key={alert.id}
              className="rounded-md border border-line-soft bg-abyss-800 px-2.5 py-2"
            >
              <div className="flex items-center gap-2">
                <span
                  aria-hidden="true"
                  className={`h-1.5 w-1.5 rounded-full ${SEVERITY[alert.severity].dot}`}
                />
                <span className="truncate text-xs font-medium text-foam">{alert.title}</span>
                <span className="ml-auto shrink-0 font-mono text-2xs text-foam-dim">
                  {alert.minutesAgo < 60
                    ? `${alert.minutesAgo}m`
                    : `${Math.round(alert.minutesAgo / 60)}h`}
                </span>
              </div>
              {!dense && (
                <p className="mt-1 text-2xs leading-relaxed text-foam-muted">{alert.detail}</p>
              )}
              <p className="mt-1 font-mono text-2xs text-foam-dim">{alert.zone}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
