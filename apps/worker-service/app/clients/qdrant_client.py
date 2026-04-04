class QdrantVectorClient:
    async def upsert_document_chunks(self, doc_id: str, chunks: list[dict]) -> None:
        _ = (doc_id, chunks)
        raise NotImplementedError("Qdrant upsert implementation is pending")


qdrant_vector_client = QdrantVectorClient()
