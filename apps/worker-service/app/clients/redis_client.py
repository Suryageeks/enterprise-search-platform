from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.core.config import settings


class RedisClient:
    def __init__(self) -> None:
        self._client: Any = None

    async def connect(self) -> Any:
        if self._client is None:
            self._client = Redis.from_url(settings.redis_url, decode_responses=True)
            await self._client.ping()
        return self._client

    async def ping(self) -> bool:
        client = await self.connect()
        await client.ping()
        return True

    async def ensure_consumer_group(self) -> None:
        client = await self.connect()
        try:
            await client.xgroup_create(
                name=settings.redis_stream_name,
                groupname=settings.redis_consumer_group,
                id="0",
                mkstream=True,
            )
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


redis_client = RedisClient()
