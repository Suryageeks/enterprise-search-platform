from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.clients.redis_client import redis_client
from app.core.config import settings
from app.schemas.ingestion import IngestionJobMessage
from app.services.ingestion_processor import ingestion_processor

logger = logging.getLogger(__name__)

class RedisConsumer:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False
    
    async def start(self) -> None:
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Redis consumer started")

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
        client = await redis_client.connect()
        
        while self._running:
            try:
                messages = await client.xreadgroup(
                    groupname=settings.redis_consumer_group,
                    consumername=settings.redis_consumer_name,
                    streams={settings.redis_stream_name: ">"},
                    count=10,
                    block=5000,
                )
                
                if not messages:
                    continue
                
                for stream_name,msgs in messages:
                    for msg_id, payload in msgs:
                        await self._handle_message(client, stream_name, msg_id, payload)
            
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(
                    "Redis consumer loop failed error_type=%s",
                    type(exc).__name__,
                )
                await asyncio.sleep(2)
    
    async def _handle_message(self, client, stream_name: str, msg_id: str, payload: dict) -> None:
        try:
            message = IngestionJobMessage(**payload)
            await ingestion_processor.process(message)
            await client.xack(stream_name, settings.redis_consumer_group, msg_id)
            logger.info("Acknowledged message %s for job %s", msg_id, message.jobId)
        except Exception as exc:
            logger.error(
                "Redis message failed id=%s error_type=%s",
                msg_id,
                type(exc).__name__,
            )

redis_consumer = RedisConsumer()
