from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

class EnterpriseAgentRequest(BaseModel):
    question: str = Field(..., min_length=1)


class EnterpriseAgentResponse(BaseModel):
    answer: str

    tool_calls: list[str] = Field(default_factory=list)

    logs: list[dict[str, Any]] = Field(default_factory=list)
    aggregations: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)

    dashboard: dict[str, Any] | None = None