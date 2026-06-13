from typing import Any

from pydantic import BaseModel, Field

class LogEvidence(BaseModel):
    timestamp: str | None = None
    service: str | None = None
    level: str | None = None
    message: str | None = None
    trace_id: str | None = None
    request_id: str | None = None
    status_code: int | None = None
    endpoint: str | None = None
    raw: dict[str, Any]

class LogAggregation(BaseModel):
    name: str
    buckets: list[dict[str, Any]] = []

class LogAgentResult(BaseModel):
    answer: str
    evidence: list[LogEvidence] = []
    aggregations: list[LogAggregation] = []

class LogTimeRange(BaseModel):
    from_time: str | None = Field(default=None, alias="from")
    to_time: str | None = Field(default=None, alias="to")


class ParsedLogQuery(BaseModel):
    service: str | None = None
    environment: str | None = None
    level: str | None = None

    trace_id: str | None = None
    request_id: str | None = None

    status_code: int | None = None
    status_code_min: int | None = None
    status_code_max: int | None = None

    endpoint: str | None = None
    exception_type: str | None = None

    time_range: LogTimeRange | None = None

    keywords: list[str] = Field(default_factory=list)
    size: int = Field(default=10, ge=1, le=100)
