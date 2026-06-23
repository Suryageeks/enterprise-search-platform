from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.execution import AgentExecutionStatus, ToolResult

class EnterpriseAgentRequest(BaseModel):
    question: str = Field(..., min_length=1)


class EnterpriseAgentResponse(BaseModel):
    answer: str
    status: AgentExecutionStatus
    tool_calls: list[str] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    logs: list[dict[str, Any]] = Field(default_factory=list)
    aggregations: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)

    dashboard: dict[str, Any] | None = None

class EnterpriseAgentStreamRequest(BaseModel):
    question: str = Field(..., min_length=1)
