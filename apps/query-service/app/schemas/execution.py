from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

class ToolExecutionStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"

class AgentExecutionStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"

class ToolErrorCode(StrEnum):
    OPENSEARCH_UNAVAILABLE = "OPENSEARCH_UNAVAILABLE"
    QDRANT_UNAVAILABLE = "QDRANT_UNAVAILABLE"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    INVALID_TOOL_INPUT = "INVALID_TOOL_INPUT"
    DASHBOARD_EXECUTION_FAILED = "DASHBOARD_EXECUTION_FAILED"
    RAG_SEARCH_FAILED = "RAG_SEARCH_FAILED"
    LOG_SEARCH_FAILED = "LOG_SEARCH_FAILED"
    LOG_AGGREGATION_FAILED = "LOG_AGGREGATION_FAILED"
    UNKNOWN_TOOL_ERROR = "UNKNOWN_TOOL_ERROR"

class ToolError(BaseModel):
    code: ToolErrorCode
    message: str
    retryable: bool = False

    details: dict[str, Any] = Field(default_factory=dict)

class ToolResult(BaseModel):
    tool: str
    status: ToolExecutionStatus

    data: dict[str, Any] | None = None
    error: ToolError | None = None

    duration_ms: int | None = Field(
        default=None,
        ge=0
    )

    @model_validator(mode="after")
    def validate_result(self) -> "ToolResult":
        if self.status == ToolExecutionStatus.SUCCESS:
            if self.error is not None:
                raise ValueError(
                    "Successful tool result cannot contain an error"
                )
            
        if self.status == ToolExecutionStatus.ERROR:
            if self.error is None:
                raise ValueError(
                    "Failed tool result must contain an error"
                )
        
        return self
    
class AgentResult(BaseModel):
    answer: str
    status: AgentExecutionStatus

    tool_results: list[ToolResult] = Field(default_factory = list)
    warnings: list[str] = Field(default_factory = list)

    logs: list[dict[str, Any]] = Field(default_factory = list)
    aggregations: list[dict[str, Any]] = Field(default_factory = list)
    sources: list[dict[str, Any]] = Field(default_factory = list)
    dashboard: dict[str, Any] | None = None
    
