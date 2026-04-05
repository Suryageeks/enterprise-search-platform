from __future__ import annotations
from turtle import st

class TextChunker:
    def chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> list[str]:
        cleaned = text.strip()
        if not cleaned:
            return []
        
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        
        chunks: list[str] = []
        start = 0
        step = chunk_size - chunk_overlap
        
        while start < len(cleaned):
            end = start + chunk_size
            chunk = cleaned[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start += step
        return chunks

text_chunker = TextChunker()
