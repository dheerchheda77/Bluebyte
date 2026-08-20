# 🌊 BlueByte AI — 4-Day Execution & Architecture Roadmap

This document outlines the system architecture, team role assignments, integration protocols, and day-by-day execution schedule for the 6-member team.

---

## 👥 Team Skill Mapping & Role Distribution

| Member | Core Focus | Assigned System Component | Primary Responsibilities |
|---|---|---|---|
| **Jaanya** | Graph Neural Networks, PyTorch Geometric | **Knowledge Graph & GNN Inference Engine** | Build heterogeneous marine graph (Species ↔ Environment ↔ Molecular eDNA), implement GNN link prediction / node classification for species distribution & food-web stability. |
| **Vivaan** | Relational, Spatial & Time-Series DBs | **Unified Marine Data Lake & Storage Engine** | PostGIS + PostgreSQL schema setup, geospatial indexing (H3 / R-Tree), InfluxDB/TimescaleDB time-series storage, ETL sanitization scripts. |
| **Shaurya** | ZeroMQ (0MQ), TCP Sockets | **High-Throughput Ingestion & Broker Service** | Build low-latency telemetry streaming engine using ZMQ PUB/SUB & ROUTER/DEALER patterns for real-time sensor/buoy telemetry & alert fanout. |
| **Pranshu** | WebSockets, FastAPI, AsyncIO | **API Gateway & Inter-Process Bridge** | Bridge 0MQ message broker with FastAPI REST & WebSocket endpoints for frontend consumption; manage worker process pools. |
| **Dheer** | Graph Algorithms, Spatial Indexing, Optimization | **Geospatial Analytics & Optimization Engine** | Custom pathfinding for vessel routes (A* / Dijkstra with ocean current cost weighting), PFZ polygon clustering (DBSCAN/KD-Tree), KD-Tree spatial queries. |
| **Diyan** | React / Next.js, Tailwind CSS, Leaflet/Mapbox | **Interactive GIS Dashboard & Analytics Portal** | Multi-layer ocean GIS visualization (SST heatmap, Chlorophyll, GNN predictions, vessel tracking), live alert popups, role-based views. |

---

## 🏛️ System Architecture & Data Flow

```
   [ Buoy/Satellite/Vessel Telemetry Stream ]
                      │ (TCP / Raw Socket)
                      ▼
       ┌──────────────────────────────┐
       │  Member 3: ZMQ Gateway Node  │ (ROUTER / DEALER & PUB/SUB)
       └──────────────┬───────────────┘
                      │ High-Speed IPC / TCP
         ┌────────────┴─────────────┐
         ▼                          ▼
┌──────────────────┐      ┌─────────────────────────┐
│ Member 2: DB ETL │      │ Member 4: Bridge/FastAPI│
│ PostGIS + TimeDB │      │ WebSocket Server        │
└────────┬─────────┘      └────────────┬────────────┘
         │                             │
         ├──────────────┐              │
         ▼              ▼              │
┌────────────────┐ ┌─────────────────┐ │
│ Member 1: GNN  │ │ Member 5: DSA   │ │
│ Bio-Prediction │ │ Spatial Compute │ │
└────────┬───────┘ └────────┬────────┘ │
         │                  │          │
         └────────┬─────────┘          │
                  ▼                    │
          [ JSON / GeoJSON ]           │
                  │                    │
                  └────────► ┌─────────┴─────────┐
                             │ Member 6: Web GIS │
                             │ Dashboard (UI)    │
                             └───────────────────┘
```

---

## 📅 4-Day Phased Execution Plan

### Day 1: Interface Contracts & Standalone Prototypes
- **Goal:** Every member works in isolation without blocking each other by agreeing strictly on JSON schemas and socket contracts.
- **Jaanya (GNN):** Define Node types (`Species`, `Location_Grid`, `eDNA_Sample`) and Edge types (`PREY_OF`, `OCCURS_IN`, `CORRELATED_WITH`). Build synthetic graph loader with PyTorch Geometric / NetworkX.
- **Vivaan (DB):** Create PostgreSQL + PostGIS schema. Load sample INCOIS SST datasets, OBIS species occurrence tables, and eDNA markers.
- **Shaurya (0MQ Lead):** Build standalone ZMQ Publisher simulating buoy stream (SST, Salinity, Current speed) emitting at 10 Hz. Build subscriber harness.
- **Pranshu (Backend/WebSockets):** Scaffold FastAPI structure, WebSocket broadcast endpoints, and mock response routes based on the API contract.
- **Dheer (DSA):** Implement standalone KD-Tree / QuadTree spatial search algorithm for nearest fish aggregation coordinates given lat/long.
- **Diyan (UI):** Set up React + Vite + Tailwind + Leaflet/Deck.gl. Render base bathymetric map and placeholder overlay toggles.

### Day 2: Pipeline Integration & Core Logic
- **Goal:** Wire components together pair-by-pair.
- **Pairs:**
  - *Pair A (Sockets + Backend):* Shaurya & Pranshu connect 0MQ stream into FastAPI WebSocket manager.
  - *Pair B (Data + Spatial Algorithms):* Vivaan & Dheer connect PostGIS queries to the DSA spatial clustering/routing algorithms.
  - *Pair C (GNN + Visualizer):* Jaanya produces predictions (e.g. biodiversity vulnerability index per grid); Diyan renders static GeoJSON layers.

### Day 3: Full End-to-End Workflow & Anomaly Triggers
- **Goal:** Complete data path: Telemetry Ingest -> Processing -> ML / Spatial computation -> Live UI updates.
- Connect live UI to FastAPI WebSocket for real-time buoy telemetry and vessel track updates.
- Implement trigger condition: If anomaly detected (e.g., sudden temperature spike + low oxygen), dispatch high-priority alert over socket to UI.
- Implement GNN-driven recommendation panel (e.g., "Given SST change in Grid X, Species Y probability drops by 42%").

### Day 4: Polish, SIH Demo Script & Presentation Preparation
- Build 3 concrete demo scenarios for evaluators:
  1. *Scenario 1:* **Potential Fishing Zone (PFZ) & Optimal Route Generation** (DSA + Ocean Currents).
  2. *Scenario 2:* **eDNA Biodiversity Cross-Verification & Link Prediction** (GNN + PostGIS).
  3. *Scenario 3:* **Real-Time Sensor Telemetry & Anomaly Trigger** (ZMQ Sockets + WebSockets + UI Alert).
- Clean code repository, check in setup scripts/Docker compose, and finalize PPT slides with architecture diagrams.

---

## 🔌 Core API & Socket Interface Contracts

### 1. ZeroMQ Telemetry Packet Format (Port 5555 / 5556)
```json
{
  "sensor_id": "INCOIS-BUOY-042",
  "timestamp": 1771600000,
  "location": { "lat": 15.2993, "lon": 73.9876 },
  "telemetry": {
    "sea_surface_temp_c": 28.4,
    "salinity_psu": 35.1,
    "chlorophyll_a_mg_m3": 1.82,
    "dissolved_oxygen_mg_l": 5.6,
    "wave_height_m": 1.2
  }
}
```

### 2. GNN & Spatial Insight Response (REST: `/api/v1/insights/grid`)
```json
{
  "grid_id": "GRID-SW-409",
  "bounding_box": [[15.0, 73.5], [15.5, 74.0]],
  "pfz_index": 0.88,
  "biodiversity_score": 0.74,
  "dominant_species_predictions": [
    { "species": "Rastrelliger kanagurta (Indian Mackerel)", "confidence": 0.91 },
    { "species": "Sardinella longiceps (Oil Sardine)", "confidence": 0.84 }
  ],
  "edna_matches": ["CYTB-SEQ-9921", "COI-FISH-1044"]
}
```
