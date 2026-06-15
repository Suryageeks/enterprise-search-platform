from __future__ import annotations

import json

from langchain_core.tools import tool

from app.services.rag_service import rag_service

@tool
async def rag_search_tool(query: str, top_k: int = 5) -> str:
    """
    Search internal documents, runbooks, knowledge base articles, and indexed RAG content.

    Use this when the user asks about documentation, known fixes, previous incidents,
    troubleshooting steps, runbooks, architecture notes, or general knowledge stored in RAG.
    """

    result = await rag_service.query(
        question=query,
        top_k=top_k,
    )

    sources = []

    for source in result.sources:
        sources.append(
            {
                "doc_id": source.doc_id,
                "file_name": source.file_name,
                "chunk_index": source.chunk_index,
                "score": source.score,
                "text_preview": source.text_preview,
            }
        )
    
    return json.dumps(
        {
            "answer": result.answer,
            "used_context": result.used_context,
            "sources": sources,
        },
        default=str
    )
