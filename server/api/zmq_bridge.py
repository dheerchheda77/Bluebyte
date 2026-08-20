"""
BlueByte AI — ZMQ-to-WebSocket Async Bridge
Subscribes to the 0MQ Stream Broker (port 5556) and pushes enriched
telemetry packets to all connected WebSocket clients in real time.
"""
import asyncio
import json
import logging
import zmq
import zmq.asyncio

logger = logging.getLogger("ZMQ-Bridge")


class ZMQBridge:
    """
    Async bridge between ZeroMQ Stream Broker and FastAPI WebSocket manager.
    Runs as a background coroutine during the FastAPI lifespan.
    """

    def __init__(self, zmq_endpoint: str = "tcp://127.0.0.1:5556"):
        self.zmq_endpoint = zmq_endpoint
        self.running = False
        self._context: zmq.asyncio.Context | None = None
        self._socket: zmq.asyncio.Socket | None = None
        self.packets_forwarded = 0
        self.anomalies_forwarded = 0

    async def start(self):
        """Start the bridge — subscribe to 0MQ and forward to WebSocket clients."""
        from server.api.websocket_manager import manager

        self._context = zmq.asyncio.Context()
        self._socket = self._context.socket(zmq.SUB)
        self._socket.connect(self.zmq_endpoint)
        self._socket.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all topics
        self.running = True

        logger.info(f"🌉 ZMQ Bridge connected to {self.zmq_endpoint} — forwarding to WebSocket clients")

        try:
            while self.running:
                try:
                    # Non-blocking poll with 100ms timeout to allow clean shutdown
                    if await self._socket.poll(timeout=100):
                        topic_bytes, payload_bytes = await self._socket.recv_multipart()
                        topic = topic_bytes.decode("utf-8")
                        payload_str = payload_bytes.decode("utf-8")

                        try:
                            payload = json.loads(payload_str)
                        except json.JSONDecodeError:
                            continue

                        # Tag the payload with its topic for frontend routing
                        payload["_topic"] = topic
                        payload["_type"] = "anomaly" if "anomaly" in topic else "telemetry"

                        # Broadcast to all connected WebSocket clients
                        await manager.broadcast(payload)

                        self.packets_forwarded += 1
                        if payload.get("anomaly_flag"):
                            self.anomalies_forwarded += 1

                        if self.packets_forwarded % 50 == 0:
                            logger.info(
                                f"📊 ZMQ Bridge stats: {self.packets_forwarded} packets forwarded | "
                                f"{self.anomalies_forwarded} anomalies | "
                                f"{manager.connection_count} WebSocket clients"
                            )

                except zmq.ZMQError as e:
                    if e.errno == zmq.ETERM:
                        break
                    logger.error(f"ZMQ error: {e}")
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("🛑 ZMQ Bridge task cancelled")
        finally:
            self._cleanup()

    def stop(self):
        """Signal the bridge to stop."""
        self.running = False

    def _cleanup(self):
        """Clean up ZMQ resources."""
        if self._socket:
            self._socket.close()
        if self._context:
            self._context.term()
        logger.info(
            f"🛑 ZMQ Bridge stopped. Total forwarded: {self.packets_forwarded} | Anomalies: {self.anomalies_forwarded}"
        )
