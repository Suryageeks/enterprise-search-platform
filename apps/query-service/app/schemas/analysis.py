from pydantic import BaseModel, Field

from app.schemas.rag import RagSource

class AnalysisQueryRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The user's question to be analyzed.")
    top_k: int = Field(default=5, ge=1, le=20, description="The number of top results to return for RAG queries.")

class AnalysisQueryResponse(BaseModel):
    intent: str
    answer: str
    sources: list[RagSource] = []
