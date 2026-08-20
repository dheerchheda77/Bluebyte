import zmq
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("TelemetrySubscriberTest")

def main():
    """
    Subscribes to the outbound stream broker (Port 5556) to verify end-to-end packet delivery.
    Pranshu's FastAPI service will use this exact socket logic to push live data to WebSockets.
    """
    endpoint = "tcp://127.0.0.1:5556"
    context = zmq.Context()
    sub_socket = context.socket(zmq.SUB)
    sub_socket.connect(endpoint)
    
    # Subscribe to both regular telemetry and critical anomalies
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
    
    logger.info(f"🎧 [TEST HARNESS ACTIVE] Listening on {endpoint} for enriched ocean telemetry...")

    try:
        while True:
            topic_bytes, payload_bytes = sub_socket.recv_multipart()
            topic = topic_bytes.decode("utf-8")
            payload = json.loads(payload_bytes.decode("utf-8"))

            if "anomaly" in topic:
                print(f"\n🚨 [CRITICAL ALERT] Topic: {topic}")
                print(f"   Sensor: {payload['sensor_id']} ({payload.get('sensor_name')})")
                print(f"   Reason: {payload.get('anomaly_reason')}")
                print(f"   Coords: [{payload['lat']}, {payload['lon']}] | SST: {payload.get('sea_surface_temp_c')}°C | DO: {payload.get('dissolved_oxygen_mg_l')} mg/L\n")
            else:
                print(f"📡 [DATA] {topic} -> SST: {payload.get('sea_surface_temp_c')}°C | Salinity: {payload.get('salinity_psu')} PSU | Z_SST: {payload.get('z_score_sst')}")

    except KeyboardInterrupt:
        logger.info("🛑 Subscriber harness closed.")
    finally:
        sub_socket.close()
        context.term()

if __name__ == "__main__":
    main()
