from __future__ import annotations
import asyncio

from langchain_openai import OpenAIEmbeddings
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

from app.core.config import settings


class EmbeddingsClient:
    def __init__(self) -> None:
        self._device = settings.embedding_device
        self._tokenizer = AutoTokenizer.from_pretrained(settings.embedding_model)
        self._model = AutoModel.from_pretrained(settings.embedding_model)
        self._model.to(self._device)
        self._model.eval()
        
    async def embed_documents(self, documents: list[str]) -> list[list[float]]:
        if not documents:
            return []
        return await asyncio.to_thread(self._embed_documents_sync, documents)

    def embedding_dimension(self) -> int:
        return int(self._model.config.hidden_size)
    
    def _embed_documents_sync(self, documents: list[str]) -> list[list[float]]:
        encoded = self._tokenizer(
            documents,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=512,
        )
        
        encoded = {key: value.to(self._device) for key, value in encoded.items()}
        
        with torch.inference_mode():
            output = self._model(**encoded)
            embeddings = self._mean_pool(
                output.last_hidden_state,
                encoded["attention_mask"],
            )
            embeddings = F.normalize(embeddings, p=2, dim=1)
            
        return embeddings.cpu().tolist()
    
    def _mean_pool(self, token_embeddings: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        masked = token_embeddings * mask
        summed = masked.sum(dim=1)
        counts = mask.sum(dim=1).clamp(min=1e-9)
        return summed / counts
        
        

embeddings_client = EmbeddingsClient()
