from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from app.schemas.execution import (
    ToolResult,
    AgentExecutionStatus
)

class CreateChatSessionRequest(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

class UpdateChatSessionRequest(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=255,
    )

class ChatSessionResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatMessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="message_metadata",
    )
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatQueryRequest(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=10_000,
    )
    
class ChatQueryResponse(BaseModel):
    session_id: UUID
    answer: str
    status: AgentExecutionStatus

    tool_calls: list[str] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    logs: list[dict[str, Any]] = Field(default_factory=list)
    aggregations: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    dashboard: dict[str, Any] | None = None

class ChatStreamRequest(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=10000
    )