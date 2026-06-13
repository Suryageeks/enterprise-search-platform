from fastapi import APIRouter, HTTPException

from app.schemas.rag import RagQueryRequest, RagQueryResponse
from app.services.rag_service import rag_service
from app.services.errors import RagServiceError

router = APIRouter(
    prefix="/api/rag",
    tags=["RAG"],
)

@router.post("/query", response_model=RagQueryResponse)
async def query_rag(request: RagQueryRequest) -> RagQueryResponse:
    try:
        return await rag_service.query(
            question=request.query,
            top_k=request.top_k,
        )
    except RagServiceError as e:
        raise HTTPException(status_code=502, detail=e.message)
