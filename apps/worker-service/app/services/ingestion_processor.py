from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, TypedDict

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, StateGraph

from app.clients.embeddings_client import embeddings_client
from app.clients.postgres_client import postgres_status_client
from app.clients.qdrant_client import qdrant_vector_client
from app.clients.s3_client import s3_client
from app.schemas.ingestion import IngestionJobMessage
from app.services.file_parser import file_parser

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_BATCH_SIZE = 32


class IngestionState(TypedDict, total=False):
    message: IngestionJobMessage
    file_bytes: bytes
    extracted_text: str
    documents: list[Document]
    embedded_batches: list[list[list[float]]]
    processed_chunks: int
    total_chunks: int
    events: list[dict[str, Any]]


class IngestionProcessor:
    def __init__(
        self,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.batch_size = batch_size
        self.graph = self._build_graph()

    async def process(self, message: IngestionJobMessage) -> None:
        await postgres_status_client.mark_processing(message.jobId, message.docId)

        try:
            async for event in self.stream(message):
                logger.info(
                    "Ingestion event job=%s doc=%s step=%s payload=%s",
                    message.jobId,
                    message.docId,
                    event["step"],
                    event,
                )
        except Exception as exc:
            logger.exception(
                "Ingestion failed for job=%s doc=%s",
                message.jobId,
                message.docId,
            )
            await postgres_status_client.mark_failed(
                message.jobId,
                message.docId,
                str(exc),
            )
            raise

    async def stream(self, message: IngestionJobMessage) -> AsyncIterator[dict[str, Any]]:
        initial_state: IngestionState = {
            "message": message,
            "processed_chunks": 0,
            "total_chunks": 0,
            "events": [],
        }

        async for event in self.graph.astream(initial_state, stream_mode="updates"):
            for step_name, payload in event.items():
                yield {
                    "step": step_name,
                    **payload,
                }

    def _build_graph(self):
        graph = StateGraph(IngestionState)

        graph.add_node("download_file", self._download_file)
        graph.add_node("extract_text", self._extract_text)
        graph.add_node("split_documents", self._split_documents)
        graph.add_node("embed_and_upsert_batches", self._embed_and_upsert_batches)
        graph.add_node("mark_completed", self._mark_completed)

        graph.set_entry_point("download_file")
        graph.add_edge("download_file", "extract_text")
        graph.add_edge("extract_text", "split_documents")
        graph.add_edge("split_documents", "embed_and_upsert_batches")
        graph.add_edge("embed_and_upsert_batches", "mark_completed")
        graph.add_edge("mark_completed", END)

        return graph.compile()

    async def _download_file(self, state: IngestionState) -> IngestionState:
        message = self._require_state_value(state, "message")
        file_bytes = await s3_client.download_bytes(message.filePath)
        events = self._require_state_value(state, "events")

        return {
            "file_bytes": file_bytes,
            "events": events + [
                {
                    "step": "download_file",
                    "status": "ok",
                    "file_path": message.filePath,
                    "bytes": len(file_bytes),
                }
            ],
        }

    async def _extract_text(self, state: IngestionState) -> IngestionState:
        message = self._require_state_value(state, "message")
        events = self._require_state_value(state, "events")
        extracted_text = await file_parser.extract_text(
            message.fileName,
            self._require_state_value(state, "file_bytes"),
        )

        return {
            "extracted_text": extracted_text,
            "events": events + [
                {
                    "step": "extract_text",
                    "status": "ok",
                    "characters": len(extracted_text),
                }
            ],
        }

    async def _split_documents(self, state: IngestionState) -> IngestionState:
        message = self._require_state_value(state, "message")
        events = self._require_state_value(state, "events")
        extracted_text = self._require_state_value(state, "extracted_text").strip()

        if not extracted_text:
            raise ValueError("Extracted text is empty")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        base_document = Document(
            page_content=extracted_text,
            metadata={
                "job_id": message.jobId,
                "doc_id": message.docId,
                "emp_id": message.empId,
                "file_name": message.fileName,
                "file_path": message.filePath,
                "upload_type": message.uploadType,
            },
        )

        documents = splitter.split_documents([base_document])

        for index, doc in enumerate(documents):
            doc.metadata["chunk_index"] = index

        return {
            "documents": documents,
            "total_chunks": len(documents),
            "events": events + [
                {
                    "step": "split_documents",
                    "status": "ok",
                    "total_chunks": len(documents),
                    "total_batches": self._batch_count(len(documents)),
                }
            ],
        }

    async def _embed_and_upsert_batches(self, state: IngestionState) -> IngestionState:
        message = self._require_state_value(state, "message")
        documents = self._require_state_value(state, "documents")
        total_chunks = self._require_state_value(state, "total_chunks")

        processed_chunks = 0
        embedded_batches: list[list[list[float]]] = []
        events = list(self._require_state_value(state, "events"))

        for batch_index, batch in enumerate(self._iter_batches(documents)):
            texts = [doc.page_content for doc in batch]
            vectors = await embeddings_client.embed_texts(texts)
            embedded_batches.append(vectors)

            payload = []
            for doc, vector in zip(batch, vectors, strict=True):
                payload.append(
                    {
                        "id": f"{message.docId}:{doc.metadata['chunk_index']}",
                        "vector": vector,
                        "payload": {
                            "text": doc.page_content,
                            "job_id": message.jobId,
                            "doc_id": message.docId,
                            "emp_id": message.empId,
                            "file_name": message.fileName,
                            "file_path": message.filePath,
                            "upload_type": message.uploadType,
                            "chunk_index": doc.metadata["chunk_index"],
                        },
                    }
                )

            await qdrant_vector_client.upsert_document_chunks(
                doc_id=message.docId,
                chunks=payload,
            )

            processed_chunks += len(batch)
            progress = round(processed_chunks / total_chunks, 4) if total_chunks else 1.0

            batch_event = {
                "step": "embed_and_upsert_batches",
                "status": "ok",
                "batch_index": batch_index,
                "batch_size": len(batch),
                "processed_chunks": processed_chunks,
                "total_chunks": total_chunks,
                "progress": progress,
            }
            events.append(batch_event)

            logger.info(
                "Processed chunk batch job=%s doc=%s batch=%s size=%s progress=%s",
                message.jobId,
                message.docId,
                batch_index,
                len(batch),
                progress,
            )

            await asyncio.sleep(0)

        return {
            "embedded_batches": embedded_batches,
            "processed_chunks": processed_chunks,
            "events": events,
        }

    async def _mark_completed(self, state: IngestionState) -> IngestionState:
        message = self._require_state_value(state, "message")
        events = self._require_state_value(state, "events")
        await postgres_status_client.mark_completed(message.jobId, message.docId)

        return {
            "events": events + [
                {
                    "step": "mark_completed",
                    "status": "ok",
                    "processed_chunks": self._require_state_value(state, "processed_chunks"),
                    "total_chunks": self._require_state_value(state, "total_chunks"),
                }
            ],
        }

    def _iter_batches(self, documents: list[Document]) -> list[list[Document]]:
        return [
            documents[index : index + self.batch_size]
            for index in range(0, len(documents), self.batch_size)
        ]

    def _batch_count(self, total_documents: int) -> int:
        if total_documents == 0:
            return 0
        return (total_documents + self.batch_size - 1) // self.batch_size

    def _require_state_value(self, state: IngestionState, key: str) -> Any:
        value = state.get(key)
        if value is None:
            raise ValueError(f"Missing required ingestion state key: {key}")
        return value


ingestion_processor = IngestionProcessor()
