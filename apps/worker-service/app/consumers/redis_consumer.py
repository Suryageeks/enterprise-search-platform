import asyncio
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisConsumer:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Redis consumer started for stream %s", settings.redis_stream_name)

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Redis consumer stopped")

    async def _run(self) -> None:
        while self._running:
            # Placeholder loop until Redis Stream consumption is implemented.
            await asyncio.sleep(1)


redis_consumer = RedisConsumer()
