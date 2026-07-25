import asyncio
import websockets
import structlog
import json
from typing import Set

logger = structlog.get_logger(__name__)

class WSServer:
    def __init__(self, host="127.0.0.1", port=8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.server = None

    async def register(self, websocket):
        self.clients.add(websocket)
        logger.info("ws_client_connected", remote_address=websocket.remote_address)

    async def unregister(self, websocket):
        self.clients.remove(websocket)
        logger.info("ws_client_disconnected", remote_address=websocket.remote_address)

    async def broadcast(self, message: dict):
        if not self.clients:
            return
        
        msg_str = json.dumps(message)
        # Create a list of awaitables for broadcasting
        tasks = [
            asyncio.create_task(client.send(msg_str))
            for client in self.clients
        ]
        if tasks:
            await asyncio.wait(tasks)

    async def _handler(self, websocket, path):
        await self.register(websocket)
        try:
            async for message in websocket:
                # Can handle incoming UI events here if necessary
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)

    async def start(self):
        self.server = await websockets.serve(self._handler, self.host, self.port)
        logger.info("ws_server_started", ws_url=f"ws://{self.host}:{self.port}")
        
    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("ws_server_stopped")
