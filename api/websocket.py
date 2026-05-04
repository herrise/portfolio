"""WebSocket bridge — subscribes to Redis pub/sub and pushes to WS clients."""
import asyncio
import json
import os
import redis.asyncio as aioredis
from fastapi import WebSocket, WebSocketDisconnect
import logging

log = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))


class LivePriceManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, message: str):
        dead = []
        for ws in self.connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = LivePriceManager()


async def redis_listener():
    """Async pub/sub listener — bridges Redis channel to WebSocket clients."""
    pubsub_client = aioredis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    async with pubsub_client.pubsub() as sub:
        await sub.subscribe("prices:live")
        log.info("redis async listener started on channel prices:live")
        async for msg in sub.listen():
            if msg["type"] == "message":
                try:
                    data = json.loads(msg["data"])
                    payload = json.dumps({"type": "prices", "data": data})
                    await manager.broadcast(payload)
                except Exception as exc:
                    log.error("broadcast error: %s", exc)


def get_manager() -> LivePriceManager:
    return manager
