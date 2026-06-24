from __future__ import annotations

import asyncio
from typing import Any

from opensearchpy import AsyncOpenSearch

from app.core.config import settings
from app.services.pii_masking_service import (
    pii_masking_service,
)


class OpenSearchLogClient:
    def __init__(self) -> None:
        http_auth = None
        if settings.opensearch_username and settings.opensearch_password:
            http_auth = (settings.opensearch_username, settings.opensearch_password)

        self._client = AsyncOpenSearch(
            hosts=[settings.opensearch_url],
            http_auth=http_auth,
            use_ssl=settings.opensearch_use_ssl,
            verify_certs=settings.opensearch_verify_certs,
        )

    async def ping(self) -> bool:
        return bool(await self._client.ping())

    async def index_log_event(self, event: dict[str, Any]) -> None:
        sanitized_event = await asyncio.to_thread(
            pii_masking_service.mask_mapping,
            event,
        )

        await self._client.index(
            index=settings.opensearch_log_index,
            body=sanitized_event,
            refresh=False,
        )

    async def bulk_index_log_events(self, events: list[dict[str, Any]]) -> None:
        if not events:
            return

        sanitized_events = await asyncio.to_thread(
            pii_masking_service.mask_mappings,
            events,
        )

        operations: list[dict[str, Any]] = []
        for event in sanitized_events:
            operations.append({"index": {"_index": settings.opensearch_log_index}})
            operations.append(event)

        await self._client.bulk(body=operations, refresh=False)

    async def close(self) -> None:
        await self._client.close()


opensearch_log_client = OpenSearchLogClient()
