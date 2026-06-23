from __future__ import annotations

from langchain_core.tools import tool

from app.schemas.execution import ToolErrorCode
from app.services.rag_service import rag_service
from app.services.tool_result_service import execute_tool, tool_error

@tool
async def rag_search_tool(query: str, top_k: int = 5) -> str:
    """
    Search internal documents, runbooks, knowledge base articles, and indexed RAG content.

    Use this when the user asks about documentation, known fixes, previous incidents,
    troubleshooting steps, runbooks, architecture notes, or general knowledge stored in RAG.
    """

    if not query.strip():
        return tool_error(
            tool="rag_search_tool",
            code=ToolErrorCode.INVALID_TOOL_INPUT,
            message="RAG query cannot be empty",
        )
    
    top_k = max(1,min(top_k,20))

    async def operation() -> dict:
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

        return {
            "answer": result.answer,
            "used_context": result.used_context,
            "sources": sources,
        }

    return await execute_tool(
        tool="rag_search_tool",
        operation=operation,
        failure_code=ToolErrorCode.RAG_SEARCH_FAILED,
        failure_message="Unable to search the knowledge base",
    )
