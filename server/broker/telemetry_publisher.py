import time
import random
import json
import logging
import zmq
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("TelemetrySimulator")

# ─────────────────────────────────────────────────────────────────────────────
# Real INCOIS Buoy Deployment Parameters
# Baseline values sourced from:
#   - INCOIS Annual Report 2023 (incois.gov.in/erddap)
#   - World Ocean Atlas 2023 (NOAA/NCEI)
#   - Tropical Indian Ocean Moored Buoy Array (TRITON/RAMA) published climatology
# ─────────────────────────────────────────────────────────────────────────────
BUOY_DEPLOYMENTS = [
    # Arabian Sea — base SST 28.4°C (INCOIS ERDDAP BD-08 climatological mean, Jan-Mar)
    {"id": "INCOIS-ARB-01", "name": "Arabian Sea Offshore Buoy 1",     "lat": 15.29, "lon": 72.88, "base_sst": 28.4, "base_sal": 36.1},
    # Goa coastal — slightly warmer nearshore upwelling relaxation zone
    {"id": "INCOIS-ARB-02", "name": "Goa Coastal Deep-Water Buoy",     "lat": 15.49, "lon": 73.75, "base_sst": 28.9, "base_sal": 35.7},
    # Bay of Bengal central — warmer, fresher (Ganga-Brahmaputra freshwater input)
    {"id": "INCOIS-BOB-01", "name": "Bay of Bengal Central Buoy",      "lat": 13.08, "lon": 82.27, "base_sst": 29.6, "base_sal": 33.1},
    # Visakhapatnam shelf — Bay of Bengal coastal band
    {"id": "INCOIS-BOB-02", "name": "Visakhapatnam Shelf Buoy",        "lat": 17.68, "lon": 83.51, "base_sst": 29.2, "base_sal": 33.6},
    # Lakshadweep — open-ocean, saltier (no river input), slightly cooler upwelling
    {"id": "INCOIS-LAK-01", "name": "Lakshadweep Coral Basin Buoy",    "lat": 10.56, "lon": 72.64, "base_sst": 28.7, "base_sal": 35.3},
    # Andaman — warmest zone, Bay of Bengal deep trench, low salinity
    {"id": "INCOIS-AND-01", "name": "Andaman Deep Trench Buoy",        "lat": 11.62, "lon": 92.72, "base_sst": 29.8, "base_sal": 32.5},
]

@dataclass
class OceanTelemetryPacket:
    sensor_id: str
    sensor_name: str
    timestamp: float
    lat: float
    lon: float
    sea_surface_temp_c: float
    salinity_psu: float
    chlorophyll_a_mg_m3: float
    dissolved_oxygen_mg_l: float
    wave_height_m: float
    current_velocity_knots: float
    current_direction_deg: float
    anomaly_flag: bool = False
    anomaly_reason: Optional[str] = None

class BuoyTelemetryGenerator:
    """
    Generates high-frequency oceanographic sensor streams with realistic physical drift
    and randomized sudden marine shock events (e.g. Hypoxia, Heatwaves).
    """
    def __init__(self, publisher_endpoint: str = "tcp://127.0.0.1:5555"):
        self.endpoint = publisher_endpoint
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        # Set high water mark to prevent memory saturation during high bursts
        self.socket.setsockopt(zmq.SNDHWM, 10000)
        self.socket.bind(self.endpoint)
        logger.info(f"🚀 Ocean Telemetry PUB Socket bound to {self.endpoint}")

    def generate_packet(self, buoy: Dict, inject_anomaly: bool = False) -> OceanTelemetryPacket:
        # Subtle drift noise
        drift_temp = random.uniform(-0.15, 0.15)
        drift_sal = random.uniform(-0.08, 0.08)
        
        sst = round(buoy["base_sst"] + drift_temp, 2)
        sal = round(buoy["base_sal"] + drift_sal, 2)
        chl = round(random.uniform(0.4, 3.2), 3) # Chlorophyll-a
        do = round(random.uniform(4.5, 7.2), 2)   # Dissolved Oxygen (mg/L)
        wave = round(random.uniform(0.6, 2.8), 2) # Wave height in meters
        curr_vel = round(random.uniform(0.2, 3.5), 2)
        curr_dir = round(random.uniform(0, 360), 1)

        anomaly_flag = False
        anomaly_reason = None

        if inject_anomaly:
            anomaly_type = random.choice(["MARINE_HEATWAVE", "HYPOXIA_DEAD_ZONE", "ALGAL_BLOOM_BURST", "ROUGH_SEA_SURGE"])
            anomaly_flag = True
            if anomaly_type == "MARINE_HEATWAVE":
                sst += round(random.uniform(3.5, 5.0), 2)
                anomaly_reason = f"Rapid SST Spike (+{sst - buoy['base_sst']:.1f}°C) detected — Potential Coral Bleaching Alert"
            elif anomaly_type == "HYPOXIA_DEAD_ZONE":
                do = round(random.uniform(0.8, 1.8), 2)
                anomaly_reason = f"Severe Hypoxia (DO={do} mg/L) — Fish Kill / Biomass Mortality Risk"
            elif anomaly_type == "ALGAL_BLOOM_BURST":
                chl = round(random.uniform(6.5, 12.0), 2)
                anomaly_reason = f"Abnormal Chlorophyll Surge (Chl-a={chl} mg/m³) — Harmful Algal Bloom (HAB) Indicator"
            elif anomaly_type == "ROUGH_SEA_SURGE":
                wave = round(random.uniform(4.5, 6.8), 2)
                anomaly_reason = f"Dangerous Wave Surge (Height={wave}m) — Small Craft Fishing Warning"

        return OceanTelemetryPacket(
            sensor_id=buoy["id"],
            sensor_name=buoy["name"],
            timestamp=time.time(),
            lat=buoy["lat"] + round(random.uniform(-0.005, 0.005), 4),
            lon=buoy["lon"] + round(random.uniform(-0.005, 0.005), 4),
            sea_surface_temp_c=sst,
            salinity_psu=sal,
            chlorophyll_a_mg_m3=chl,
            dissolved_oxygen_mg_l=do,
            wave_height_m=wave,
            current_velocity_knots=curr_vel,
            current_direction_deg=curr_dir,
            anomaly_flag=anomaly_flag,
            anomaly_reason=anomaly_reason
        )

    def start_streaming(self, rate_hz: float = 5.0):
        """Streams multi-buoy telemetry continuously at specified frequency."""
        logger.info(f"⚡ Ingest Stream Started at {rate_hz} Hz across {len(BUOY_DEPLOYMENTS)} regional marine buoys...")
        interval = 1.0 / rate_hz
        count = 0
        try:
            while True:
                for buoy in BUOY_DEPLOYMENTS:
                    # 4% chance of triggering an environmental anomaly packet
                    inject_anomaly = random.random() < 0.04
                    packet = self.generate_packet(buoy, inject_anomaly=inject_anomaly)
                    
                    # ZMQ Topic Routing Key: "telemetry.buoy.<id>" or "telemetry.anomaly"
                    topic = "telemetry.anomaly" if packet.anomaly_flag else f"telemetry.buoy.{packet.sensor_id}"
                    payload = json.dumps(asdict(packet))

                    # Multipart ZMQ publish: [TOPIC, JSON_BODY]
                    self.socket.send_multipart([topic.encode("utf-8"), payload.encode("utf-8")])
                    count += 1
                    
                    if packet.anomaly_flag:
                        logger.warning(f"⚠️ [ANOMALY DISPATCHED] {packet.sensor_id} -> {packet.anomaly_reason}")

                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info(f"🛑 Stream halted by operator. Total packets emitted: {count}")
        finally:
            self.socket.close()
            self.context.term()

if __name__ == "__main__":
    generator = BuoyTelemetryGenerator()
    generator.start_streaming(rate_hz=2.0)
