"""FastAPI serving layer — REST + WebSocket for Lambda Architecture portfolio."""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from routes.prices import router as prices_router
from routes.pipeline import router as pipeline_router
from websocket import manager, redis_listener

logging.basicConfig(level=logging.INFO, format="%(asctime)s [api] %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start Redis pub/sub listener in background
    task = asyncio.create_task(redis_listener())
    log.info("API started — Lambda Architecture serving layer")
    yield
    task.cancel()
    log.info("API shutting down")


app = FastAPI(title="Crypto Pipeline API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prices_router)
app.include_router(pipeline_router)


@app.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep-alive
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)


@app.get("/health")
def health():
    return {"status": "ok"}
