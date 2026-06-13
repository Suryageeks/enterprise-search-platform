from pydantic import BaseModel, Field

from typing import Any

from app.schemas.rag import RagSource
from app.schemas.logs import LogAggregation, LogEvidence

class AnalysisQueryRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The user's question to be analyzed.")
    top_k: int = Field(default=5, ge=1, le=20, description="The number of top results to return for RAG queries.")

class AnalysisQueryResponse(BaseModel):
    intent: str
    answer: str
    sources: list[RagSource] = []
    used_context: bool = False

    evidence: list[LogEvidence] = []
    aggregations: list[LogAggregation] = []
    dashboard: dict[str, Any] | None = None


