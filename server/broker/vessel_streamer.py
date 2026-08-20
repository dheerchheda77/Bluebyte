import time
import json
import logging
import zmq
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("VesselRadarSimulator")

VESSELS = [
    {"vessel_id": "IND-FSH-7890", "name": "Sagar Kanya III", "flag": "IND", "lat": 15.10, "lon": 73.10, "speed_knots": 8.5, "heading_deg": 240.0, "vessel_type": "Trawler"},
    {"vessel_id": "IND-FSH-1102", "name": "Matsya Ratna", "flag": "IND", "lat": 13.20, "lon": 81.90, "speed_knots": 6.2, "heading_deg": 110.0, "vessel_type": "Gillnetter"},
    {"vessel_id": "IND-RES-0044", "name": "NIO Research Explorer", "flag": "IND", "lat": 15.35, "lon": 73.65, "speed_knots": 11.0, "heading_deg": 180.0, "vessel_type": "Scientific Research"},
    {"vessel_id": "UNK-IUU-9912", "name": "Dark Ghost Vessel", "flag": "UNKNOWN", "lat": 10.12, "lon": 74.50, "speed_knots": 14.2, "heading_deg": 45.0, "vessel_type": "Suspected IUU Fishing"},
]

class VesselRadarStreamer:
    """
    Simulates Automatic Identification System (AIS) transponder feeds from fishing & research vessels.
    Emits vessel position & status over ZeroMQ directly to the broker.
    """
    def __init__(self, endpoint: str = "tcp://127.0.0.1:5555"):
        self.endpoint = endpoint
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.connect(self.endpoint)
        logger.info(f"🛰️ AIS Vessel Radar Streamer connected to {self.endpoint}")

    def run(self, interval_sec: float = 1.0):
        logger.info(f"🚢 Tracking {len(VESSELS)} marine vessels across the Indian EEZ...")
        try:
            while True:
                for v in VESSELS:
                    # Simulate navigation drift
                    v["lat"] += (0.001 * (v["speed_knots"] / 10.0))
                    v["lon"] += (0.001 * (v["speed_knots"] / 10.0))

                    # Random AIS speed fluctuation
                    payload = {
                        "sensor_id": v["vessel_id"],
                        "sensor_name": v["name"],
                        "vessel_type": v["vessel_type"],
                        "flag": v["flag"],
                        "timestamp": time.time(),
                        "lat": round(v["lat"], 4),
                        "lon": round(v["lon"], 4),
                        "speed_knots": v["speed_knots"],
                        "heading_deg": v["heading_deg"],
                        "anomaly_flag": v["flag"] == "UNKNOWN",
                        "anomaly_reason": "IUU Warning: Unregistered vessel operating in Indian EEZ with AIS spoofing risk" if v["flag"] == "UNKNOWN" else None
                    }

                    topic = "telemetry.anomaly" if payload["anomaly_flag"] else f"telemetry.vessel.{v['vessel_id']}"
                    self.socket.send_multipart([topic.encode("utf-8"), json.dumps(payload).encode("utf-8")])

                time.sleep(interval_sec)
        except KeyboardInterrupt:
            logger.info("🛑 AIS Streamer stopped.")
        finally:
            self.socket.close()
            self.context.term()

if __name__ == "__main__":
    streamer = VesselRadarStreamer()
    streamer.run()
