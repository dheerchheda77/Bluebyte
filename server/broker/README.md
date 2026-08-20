# ⚡ BlueByte Ocean Stream Broker & Ingestion Engine
**Author:** Shaurya (Network & Streaming Engineer)  
**Module:** `server/broker/`

---

## 🌊 Overview
The **Ocean Stream Broker** is the high-speed sensory nervous system of **BlueByte AI**. It ingests high-frequency marine telemetry streams from distributed Indian Ocean observation buoys (INCOIS Arabian Sea, Bay of Bengal, Lakshadweep, Andaman) and Automatic Identification System (AIS) transponders from marine vessels over ZeroMQ (0MQ) TCP sockets.

### 🚀 Key Technical Highlights
1. **Ultra-Low Latency Ingestion:** Uses ZeroMQ `PUB/SUB` sockets with custom High-Water-Mark buffer safety (`SNDHWM=10000`).
2. **In-Memory Streaming Anomaly Detection:** Calculates dynamic Z-scores using an $O(1)$ sliding window per sensor for Sea Surface Temperature (SST) and Dissolved Oxygen (DO) to detect sudden marine heatwaves, hypoxia dead zones, and algal bloom surges without hitting a database.
3. **Multi-Source Data Ingestion:**
   - **Ocean Buoys:** SST (°C), Salinity (PSU), Chlorophyll-a (mg/m³), Dissolved Oxygen (mg/L), Wave Height (m), Current Velocity & Direction.
   - **AIS Transponders:** Vessel ID, GPS Coordinates, Heading, Speed, Flag, and Illegal, Unreported & Unregulated (IUU) fishing risk detection.
4. **Dynamic Topic Routing:** Dispatches packets to `stream.telemetry.<sensor_id>` for normal streams and elevates critical alerts to `stream.critical.anomaly` for instant push to Pranshu's WebSocket Gateway.

---

## 📁 Files in this Module

| File | Description |
|---|---|
| [`stream_broker.py`](file:///c:/Users/Shaurya/OneDrive/Desktop/SIH/server/broker/stream_broker.py) | **The Core Broker:** Ingests from port `5555`, executes statistical Z-score calculations, and fans out enriched streams on port `5556`. |
| [`telemetry_publisher.py`](file:///c:/Users/Shaurya/OneDrive/Desktop/SIH/server/broker/telemetry_publisher.py) | **Ocean Buoy Streamer:** Simulates continuous high-frequency telemetry across 6 real Indian coastal and deep-sea coordinates. |
| [`vessel_streamer.py`](file:///c:/Users/Shaurya/OneDrive/Desktop/SIH/server/broker/vessel_streamer.py) | **AIS Vessel Radar:** Simulates live trawler, research vessel, and IUU dark vessel GPS trajectories. |
| [`test_subscriber.py`](file:///c:/Users/Shaurya/OneDrive/Desktop/SIH/server/broker/test_subscriber.py) | **Test Harness:** Real-time terminal client showing live packet metrics and critical alert triggers. |
| [`requirements.txt`](file:///c:/Users/Shaurya/OneDrive/Desktop/SIH/server/broker/requirements.txt) | Module dependencies (`pyzmq`, `numpy`, `pydantic`). |

---

## 🏃 How to Run Locally

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Streaming Architecture (in 3 separate terminals):

**Terminal 1: Start the Broker (The Core Service)**
```bash
python stream_broker.py
```

**Terminal 2: Start the Ingestion Test Subscriber**
```bash
python test_subscriber.py
```

**Terminal 3: Launch the Ocean Buoy & Vessel Streams**
```bash
python telemetry_publisher.py
# (Optionally run vessel_streamer.py in a 4th terminal)
```

---

## 🔌 Socket Contract for Teammates (Pranshu & Vivaan)

- **Outbound Ingestion Endpoint:** `tcp://127.0.0.1:5556`
- **Socket Type:** ZeroMQ `SUB`
- **Topic Prefixes:**
  - `stream.telemetry.*` $\rightarrow$ Standard enriched sensor data
  - `stream.critical.anomaly` $\rightarrow$ Immediate UI Alert & Database Trigger
