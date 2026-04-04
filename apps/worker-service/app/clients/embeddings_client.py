class EmbeddingsClient:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        _ = texts
        raise NotImplementedError("Embedding implementation is pending")


embeddings_client = EmbeddingsClient()
