import structlog
import asyncio
from websockets.server import serve
import json

logger = structlog.get_logger(__name__)

class ARHUDStreamer:
    """Streams M.Y.R.A state to WebXR/OpenVR endpoints via WebSocket"""
    def __init__(self, host="127.0.0.1", port=8765):
        self.host = host
        self.port = port
        self.clients = set()
        self.server_task = None
        logger.info(f"ARHUDStreamer initialized on ws://{host}:{port}")

    async def _handler(self, websocket):
        self.clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)

    async def start(self):
        self.server_task = await serve(self._handler, self.host, self.port)
        logger.info("ARHUDStreamer WebSocket server started.")

    async def broadcast_state(self, state: str, message: str = ""):
        payload = json.dumps({"state": state, "message": message})
        if self.clients:
            for client in self.clients:
                try:
                    await client.send(payload)
                except Exception as e:
                    logger.error("Failed to send HUD payload", error=str(e))

    async def stop(self):
        if self.server_task:
            self.server_task.close()
            await self.server_task.wait_closed()
            logger.info("ARHUDStreamer WebSocket server stopped.")
