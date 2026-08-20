"""
BlueByte AI — WebSocket Manager
Manages real-time WebSocket connections for live telemetry streaming to browser clients.
"""
import asyncio
import json
import logging
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("WebSocketManager")
router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts telemetry data."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        client = websocket.client
        logger.info(f"🔗 Client connected: {client.host}:{client.port} | Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"🔌 Client disconnected | Remaining: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send a message to all connected WebSocket clients."""
        if not self.active_connections:
            return

        payload = json.dumps(message)
        disconnected = set()

        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_text(payload)
                except Exception:
                    disconnected.add(connection)

            # Clean up dead connections
            self.active_connections -= disconnected

    async def broadcast_raw(self, payload_str: str):
        """Send a pre-serialized string to all connected clients."""
        if not self.active_connections:
            return

        disconnected = set()
        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_text(payload_str)
                except Exception:
                    disconnected.add(connection)
            self.active_connections -= disconnected

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws/live-telemetry")
async def websocket_endpoint(websocket: WebSocket):
    """
    Live telemetry WebSocket endpoint.
    Clients connect here to receive real-time ocean sensor data and anomaly alerts.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; receive any client messages (e.g., filter preferences)
            data = await websocket.receive_text()
            try:
                client_msg = json.loads(data)
                logger.debug(f"Client message received: {client_msg}")
                # Future: handle client-side filter subscriptions here
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)
