from __future__ import annotations

import asyncio

import torch
import torch.nn.functional as F
from langchain_core.embeddings import Embeddings
from transformers import AutoModel, AutoTokenizer

from app.core.config import settings

class BertEmbeddings(Embeddings):
    def __init__(self) -> None:
        self.device = settings.embedding_device
        self.tokenizer = AutoTokenizer.from_pretrained(settings.embedding_model)
        self.model = AutoModel.from_pretrained(settings.embedding_model).to(self.device)
        self.model.eval()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._embed_sync(texts)
    
    def embed_query(self, text: str) -> list[float]:
        return self._embed_sync([text])[0]
    
    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self.embed_documents, texts)
    
    async def aembed_query(self, text: str) -> list[float]:
        return await asyncio.to_thread(self.embed_query, text)
    
    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=512,
        )

        encoded = {
            key: value.to(self.device)
            for key, value in encoded.items()
        }
    
        with torch.inference_mode():
            outputs = self.model(**encoded)

            embeddings = self._mean_pool(
                outputs.last_hidden_state,
                encoded["attention_mask"],
            )

            embeddings = F.normalize(embeddings, p=2, dim=1)

        return embeddings.cpu().tolist()
    
    def _mean_pool(self, token_embeddings: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()

        masked_embeddings = token_embeddings * mask
        summed = masked_embeddings.sum(dim=1)
        counts = mask.sum(dim=1).clamp(min=1e-9)
        mean_pooled = summed / counts

        return mean_pooled
    

