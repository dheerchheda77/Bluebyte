import time
import json
import logging
import zmq
from collections import deque
from typing import Dict, Deque, Tuple, Optional
import math

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("StreamProcessor")

class SlidingWindowStats:
    """Maintains an in-memory sliding window of metric values with O(1) streaming updates."""
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.sst_window: Deque[float] = deque(maxlen=window_size)
        self.sal_window: Deque[float] = deque(maxlen=window_size)
        self.do_window: Deque[float] = deque(maxlen=window_size)

    def add(self, sst: float, sal: float, do: float):
        self.sst_window.append(sst)
        self.sal_window.append(sal)
        self.do_window.append(do)

    def compute_zscore(self, val: float, window: Deque[float]) -> float:
        if len(window) < 5:
            return 0.0
        mean = sum(window) / len(window)
        variance = sum((x - mean) ** 2 for x in window) / len(window)
        std = math.sqrt(variance) if variance > 1e-6 else 1e-6
        return (val - mean) / std

class OceanStreamBroker:
    """
    Core Ingestion & Broker Engine:
    1. Subscribes to raw telemetry from Sensor Publishers (SUB socket on tcp://127.0.0.1:5555)
    2. Performs low-latency in-memory Sliding Window Statistical Anomaly Detection (Z-Score & Thresholds)
    3. Publishes enriched, anomaly-flagged packets downstream to FastAPI WebSocket bridge & DB (PUB socket on tcp://127.0.0.1:5556)
    """
    def __init__(
        self,
        inbound_endpoint: str = "tcp://127.0.0.1:5555",
        outbound_endpoint: str = "tcp://127.0.0.1:5556"
    ):
        self.inbound_endpoint = inbound_endpoint
        self.outbound_endpoint = outbound_endpoint
        
        self.context = zmq.Context()
        
        # Inbound SUB socket
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(self.inbound_endpoint)
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "") # Subscribe to all topics
        
        # Outbound PUB socket
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(self.outbound_endpoint)

        # In-memory per-sensor sliding windows
        self.sensor_windows: Dict[str, SlidingWindowStats] = {}
        self.total_processed = 0
        self.total_anomalies = 0

        logger.info(f"🟢 [BROKER INITIALIZED] Inbound SUB connected to {inbound_endpoint} | Outbound PUB bound to {outbound_endpoint}")

    def process_packet(self, raw_payload: Dict) -> Tuple[Dict, str]:
        sensor_id = raw_payload.get("sensor_id", "UNKNOWN")
        if sensor_id not in self.sensor_windows:
            self.sensor_windows[sensor_id] = SlidingWindowStats(window_size=30)

        stats = self.sensor_windows[sensor_id]
        sst = raw_payload.get("sea_surface_temp_c", 0.0)
        sal = raw_payload.get("salinity_psu", 0.0)
        do = raw_payload.get("dissolved_oxygen_mg_l", 0.0)

        # Calculate Z-score before appending
        z_sst = stats.compute_zscore(sst, stats.sst_window)
        z_do = stats.compute_zscore(do, stats.do_window)
        stats.add(sst, sal, do)

        # Auto-enrich packet with real-time statistical metrics
        raw_payload["z_score_sst"] = round(z_sst, 2)
        raw_payload["z_score_do"] = round(z_do, 2)
        raw_payload["processed_at_epoch"] = time.time()

        # Check if statistically aberrant (|Z| > 2.8) or if explicitly flagged by sensor
        is_stat_anomaly = abs(z_sst) > 2.8 or abs(z_do) > 2.8
        if is_stat_anomaly and not raw_payload.get("anomaly_flag", False):
            raw_payload["anomaly_flag"] = True
            raw_payload["anomaly_reason"] = f"Statistical Outlier Detected: Z_SST={z_sst:.1f}, Z_DO={z_do:.1f}"

        # Determine downstream dispatch routing topic
        if raw_payload.get("anomaly_flag", False):
            topic = "stream.critical.anomaly"
            self.total_anomalies += 1
        else:
            topic = f"stream.telemetry.{sensor_id}"

        self.total_processed += 1
        return raw_payload, topic

    def run(self):
        logger.info("🌊 [BROKER ENGINE RUNNING] Listening for high-speed sensor frames...")
        try:
            while True:
                topic_bytes, payload_bytes = self.sub_socket.recv_multipart()
                try:
                    payload = json.loads(payload_bytes.decode("utf-8"))
                    enriched_payload, outbound_topic = self.process_packet(payload)
                    
                    # Forward enriched packet over outbound PUB socket
                    self.pub_socket.send_multipart([
                        outbound_topic.encode("utf-8"),
                        json.dumps(enriched_payload).encode("utf-8")
                    ])

                    if enriched_payload.get("anomaly_flag", False):
                        logger.warning(
                            f"🚨 [BROKER ALERT] Sensor={enriched_payload['sensor_id']} | "
                            f"Issue: {enriched_payload.get('anomaly_reason')} | "
                            f"Topic: {outbound_topic}"
                        )
                    elif self.total_processed % 20 == 0:
                        logger.info(f"📊 Processed {self.total_processed} packets | Anomalies filtered: {self.total_anomalies}")

                except Exception as e:
                    logger.error(f"Error parsing packet: {e}")

        except KeyboardInterrupt:
            logger.info(f"🛑 Broker stopped. Total handled: {self.total_processed} | Anomalies: {self.total_anomalies}")
        finally:
            self.sub_socket.close()
            self.pub_socket.close()
            self.context.term()

if __name__ == "__main__":
    broker = OceanStreamBroker()
    broker.run()
