from fastapi import APIRouter

from app.schemas.rag import RagQueryRequest, RagQueryResponse
from app.services.rag_service import rag_service

router = APIRouter(
    prefix="/api/rag",
    tags=["RAG"],
)

@router.post("/query", response_model=RagQueryResponse)
async def query_rag(request: RagQueryRequest) -> RagQueryResponse:
    return await rag_service.query(
        question=request.query,
        top_k=request.top_k,
    )