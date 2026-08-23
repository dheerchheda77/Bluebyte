# BlueByte AI — UI/UX Design Document

| | |
|---|---|
| **Document Version** | 1.0 |
| **Scope** | (A) The built GIS Operations Dashboard — specified as-implemented in `client/`. (B) Planned surfaces (mobile app, admin console) — specified as design direction, not implementation. |
| **Companion documents** | PRD, SRS, Architecture Document |

---

## 1. Design Philosophy

BlueByte's one built interface is a **"Dark Marine Theme" operations dashboard** — the visual language of a ship's bridge or a mission-control room, not a marketing website. This is a deliberate choice, not a default: the primary early persona is a **researcher/operator monitoring live conditions**, where a dark, high-contrast, glanceable interface reduces eye strain during long monitoring sessions and makes anomaly-colored elements (red/orange) pop immediately against a near-black background.

Three principles run through every screen, built or planned:
1. **Glanceability over completeness.** A fisherman or operator should be able to tell "is something wrong right now?" in under two seconds, before reading any detail.
2. **Live state is always visible.** Connection status, not just data, is a first-class UI element — because in this domain, stale data silently presented as current is dangerous.
3. **Never a blank screen.** Every panel has an explicit loading/empty/error state (mirroring the backend's own "always return something" philosophy — see Architecture Document §1).

---

## 2. Personas & Primary Journeys

| Persona | Primary Journey (today) | Primary Journey (planned) |
|---|---|---|
| Marine Researcher | Open dashboard → scan map for anomaly markers → open species-prediction panel → correlate with SST chart | Same, plus knowledge-graph query search |
| Policymaker | *(no dedicated surface yet — uses same dashboard)* | Open Admin Console → view aggregated regional analytics → run MPA "what-if" simulation |
| Fisherman | *(no dedicated surface yet)* | Open mobile app → see nearest PFZ in local language → get storm/hazard push alert |
| Coast Guard | View vessel layer on dashboard, notice flagged vessel | Receive push alert on suspected IUU vessel with track history |

---

## 3. Built Surface: The GIS Operations Dashboard

### 3.1 Screen Layout (as implemented in `client/index.html`)

```
┌───────────────────────────────────────────────────────────────────────┐
│ NAVBAR: 🌊 BlueByte AI logo   |   ● Connecting.../Connected  |  Clock  │
├───────────────┬───────────────────────────────────────────────────────┤
│  SIDEBAR       │                                                       │
│  (300px)       │                                                       │
│                │                                                       │
│ ▾ Layer        │                                                       │
│   Controls     │                                                       │
│  ☑ Heatmap     │                    MAP (Leaflet)                     │
│  ☑ Buoys       │        centered [14°N, 78°E], zoom 5                 │
│  ☑ Vessels     │        dark CartoDB basemap                          │
│  ☑ PFZ Zones   │        + legend                                      │
│  ☑ Anomalies   │                                                       │
│                │                                                       │
│ ▾ Species      │                                                       │
│   Predictions  │                                                       │
│  [live list]   │                                                       │
│                │                                                       │
│ ▾ Active       │                                                       │
│   Alerts       │                                                       │
│  [live list]   │                                                       │
├───────────────┴───────────────────────────────────────────────────────┤
│  CHARTS STRIP:   [ SST time series ]  [ Salinity ]  [ Dissolved O₂ ]  │
└───────────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Inventory

| Component | Behavior |
|---|---|
| **Navbar connection dot** | Red by default; turns green with a soft pulsing glow the instant `/ws/live-telemetry` connects (`TelemetryWebSocket` class). Text reads "Connecting…" → "Connected". |
| **Live clock** | Monospace, cyan — reinforces "this is a live system," not a static report. |
| **Collapsible sidebar panels** | Each panel (Layer Controls / Species Predictions / Active Alerts) toggles open/closed independently via a header click, so an operator can focus on one concern at a time. |
| **Layer toggle checkboxes** | Five independent layers (heatmap, buoys, vessels, PFZ, anomalies), each backed by its own Leaflet `LayerGroup`, added/removed from the map without re-fetching data. |
| **Buoy markers** | Circle markers in accent cyan; clicking opens a popup with sensor name and current SST / Salinity / DO / Chlorophyll, each formatted to 2 decimal places, with an em-dash fallback (`--`) when a value is missing rather than showing `undefined` or `NaN`. |
| **Species Predictions panel** | Live list, shows a "Loading predictions…" placeholder state until the first data arrives — never appears empty by accident. |
| **Active Alerts panel** | Live list; shows an explicit system-initialized placeholder ("System initialized. Awaiting data...") before the first alert arrives. |
| **Charts strip** | Three Chart.js canvases (SST, Salinity, Dissolved Oxygen) as rolling time-series, updated as new telemetry streams in. |
| **Legend** | Rendered directly onto the map (via `addLegend()`), so layer meaning doesn't require leaving the map to check the sidebar. |

### 3.3 Interaction Flows

**Flow: Live telemetry arrives**
1. `TelemetryWebSocket` receives a JSON packet over `/ws/live-telemetry`.
2. If it's a normal reading → `map.addBuoyReading(data)` updates or creates the marker in-place (matched by `sensor_id`, so markers move/update rather than duplicate) and the relevant chart appends a new point.
3. If it's flagged as an anomaly → in addition to the above, it's pushed into the Active Alerts panel with severity-appropriate styling.

**Flow: Connection drop**
1. Socket closes → connection dot turns red, text reverts to a disconnected state.
2. `TelemetryWebSocket` retries with exponential backoff, capped at 30 seconds, so it doesn't hammer the server but also doesn't require a manual page refresh to recover.

**Flow: Operator narrows focus**
1. Operator unchecks "Vessels" and "Heatmap" to reduce visual clutter while investigating a specific alert.
2. Map immediately removes those layer groups; species/alert panels are unaffected (independent state).

### 3.4 Visual Design System (extracted from `client/css/style.css`)

| Token | Value | Usage |
|---|---|---|
| `--bg-color` | `#0a0e27` | App background (near-black navy) |
| `--sidebar-bg` | `#0d1333` | Navbar + sidebar background |
| `--card-bg` | `rgba(19, 26, 69, 0.7)` | Panel content, translucent with backdrop blur |
| `--text-primary` | `#ffffff` | Primary text |
| `--text-secondary` | `#8e9bb0` | Secondary/status text |
| `--accent-cyan` | `#00e5ff` | Brand accent, live/connected state, buoy markers |
| `--accent-orange` | `#ff6f00` | Medium-severity accents |
| `--accent-red` | `#ff1744` | Disconnected state, critical alerts |
| `--accent-green` | `#00e676` | Connected state, positive/healthy indicators |
| `--glow-cyan` / `--glow-red` | soft box-shadow glows | Draws the eye to state changes (connection, critical alerts) without needing motion |
| Font | `'Segoe UI', Tahoma, Geneva, Verdana, sans-serif` | System-native, no custom font load — keeps first paint fast |
| Scrollbars | Custom-styled, thin, cyan thumb on navy track | Keeps the "instrument panel" feel even in scrollable areas |

**Severity color mapping (recommended convention, consistent with existing palette):**

| Severity | Color |
|---|---|
| `critical` | `--accent-red`, with glow |
| `high` | `--accent-red`, no glow |
| `medium` | `--accent-orange` |
| `low` | `--text-secondary` (muted, no accent) |

### 3.5 Accessibility & Readability Notes (current state)
- High contrast (white/cyan text on near-black background) supports outdoor/bright-light legibility, an important real-world condition for anyone using this at sea or on a boat deck.
- No `aria-*` roles or keyboard-navigation handling currently exist in `index.html`; this should be added before any public/production rollout (see Planned Improvements below).
- No responsive/mobile breakpoint exists — the current layout assumes a desktop-width viewport.

---

## 4. Planned Surfaces (Design Direction, Not Yet Built)

### 4.1 Mobile App (Fisherman-Facing)

**Design intent:** the opposite emphasis of the dashboard — radical simplification, not comprehensive monitoring. A fisherman needs three answers, in order: *Is it safe to go out? Where should I go? Is anything wrong right now?*

Proposed screen inventory:

| Screen | Content | Why |
|---|---|---|
| **Home / Today** | One large PFZ recommendation card (nearest high-score zone, distance, dominant species) + a prominent safety banner (wave height / storm status) above it | Safety must never be below the fold |
| **Map** | Simplified version of the dashboard map — PFZ + hazard layers only, no species/GNN internals | Reduces cognitive load; the ML detail is for researchers, not end consumers |
| **Alerts** | Push-notification history, filterable by severity | Matches the existing `alerts` data model 1:1 — no new backend needed |
| **Language Selector** | Switches all copy + voice alerts | Supports the 6 named regional languages (Hindi, Tamil, Telugu, Malayalam, Bengali, Odia) |

**Key constraint driving the design:** low-end hardware, intermittent 2G/3G. This implies: vector-tile map layers instead of raster imagery, aggressive caching of "last known good" state so the app is still useful offline, and voice-based alert playback as an alternative to reading text.

### 4.2 Admin / Analytics Console (Policymaker-Facing)

**Design intent:** aggregate, not real-time-operational. Where the dashboard answers "what's happening right now at this buoy," the console answers "what's the trend across this region this season."

Proposed modules:
- Regional heatmap of alert frequency over time (overfishing hotspots, recurring HAB zones).
- MPA "what-if" simulation panel (policy simulation module from the vision).
- Role-based access so this console is only reachable by the Policymaker/Admin persona once RBAC exists.

### 4.3 GIS Explorer (Researcher-Facing extension)

An extension of the existing dashboard rather than a new app: add a knowledge-graph query bar ("show me eDNA hits within 50km of any SST anomaly in the last 30 days") once the Neo4j migration (Architecture Document §6) lands.

---

## 5. Usability Heuristics Applied

| Heuristic | How it shows up today |
|---|---|
| **Visibility of system status** | Connection dot, clock, per-panel loading states |
| **Match between system and real world** | Buoy names use real INCOIS-style naming (e.g., "Goa Coastal Deep-Water Buoy") rather than opaque IDs alone |
| **Error prevention** | Numeric fields fall back to `--` instead of showing `NaN`/`undefined` when data is momentarily missing |
| **Recognition over recall** | Layer toggles are always visible in the sidebar, not buried in a menu |
| **Aesthetic & minimalist design** | Collapsible panels let an operator hide sections they don't currently need |
| **Flexibility & efficiency of use** | Independent layer toggles let power users tailor the view per-task |

---

## 6. Planned Improvements (Not Yet Implemented)

- Keyboard navigation and ARIA labeling for accessibility compliance.
- Responsive breakpoints for tablet/mobile web access to the existing dashboard (separate from the dedicated mobile app).
- Persisted user preferences (which layers/panels are open) — currently resets on reload.
- Sound/vibration cues for `critical` alerts, not just color, for operators who aren't looking directly at the screen.
- A visible legend key for severity colors directly in the Active Alerts panel header (currently only implied by color, not labeled).
