from __future__ import annotations

import asyncio

from qdrant_client import AsyncQdrantClient, models

from app.core.config import settings


class QdrantVectorClient:
    def __init__(self) -> None:
        self._client = AsyncQdrantClient(url=settings.qdrant_url)
        self._collection_checked = False
        self._collection_lock = asyncio.Lock()

    async def upsert_document_chunks(self, doc_id: str, chunks: list[dict]) -> None:
        _ = doc_id
        if not chunks:
            return

        await self._ensure_collection(vector_size=len(chunks[0]["vector"]))

        points = [
            models.PointStruct(
                id=chunk["id"],
                vector=chunk["vector"],
                payload=chunk["payload"],
            )
            for chunk in chunks
        ]

        await self._client.upsert(
            collection_name=settings.qdrant_collection_name,
            points=points,
            wait=True,
        )

    async def _ensure_collection(self, vector_size: int) -> None:
        if self._collection_checked:
            return

        async with self._collection_lock:
            if self._collection_checked:
                return

            exists = await self._client.collection_exists(
                collection_name=settings.qdrant_collection_name,
            )
            if not exists:
                await self._client.create_collection(
                    collection_name=settings.qdrant_collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=self._parse_distance(settings.qdrant_vector_distance),
                    ),
                )

            self._collection_checked = True

    def _parse_distance(self, value: str) -> models.Distance:
        normalized = value.strip().lower()
        if normalized == "cosine":
            return models.Distance.COSINE
        if normalized == "dot":
            return models.Distance.DOT
        if normalized == "euclid":
            return models.Distance.EUCLID
        if normalized == "manhattan":
            return models.Distance.MANHATTAN
        raise ValueError(f"Unsupported Qdrant distance: {value}")


qdrant_vector_client = QdrantVectorClient()
