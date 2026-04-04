from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.clients.postgres_client import postgres_status_client
from app.clients.redis_consumer import redis_consumer
from app.consumers.redis_consumer import redis_consumer
from app.clients.redis_client import redis_client
from app.db.database import close_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    await postgres_status_client.ping()
    await redis_client.connect()
    await redis_client.ensure_consumer_group()
    await redis_consumer.start()
    
    try:
        yield
    finally:
        await redis_consumer.stop()
        await redis_client.close()
        await close_db()


app = FastAPI(
    title="worker-service",
    version="0.1.0",
    lifespan=lifespan,
)

@app.get("/health")
async def health() -> dict[str, str]:
    await postgres_status_client.ping()
    await redis_client.ping()
    return {"status": "ok"}
