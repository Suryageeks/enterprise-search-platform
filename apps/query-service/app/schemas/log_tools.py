from enum import StrEnum

from pydantic import BaseModel, Field


SAFE_IDENTIFIER_PATTERN = r"^[A-Za-z0-9._-]+$"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class AggregationField(StrEnum):
    SERVICE = "service"
    LEVEL = "level"
    STATUS_CODE = "status_code"
    ENDPOINT = "endpoint"
    EXCEPTION_TYPE = "exception_type"


class SafeLogSearchInput(BaseModel):
    query: str = Field(default="", max_length=500)
    service: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=SAFE_IDENTIFIER_PATTERN,
    )
    environment: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        pattern=SAFE_IDENTIFIER_PATTERN,
    )
    level: LogLevel | None = None
    trace_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        pattern=SAFE_IDENTIFIER_PATTERN,
    )
    request_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        pattern=SAFE_IDENTIFIER_PATTERN,
    )
    size: int = Field(default=10, ge=1, le=100)


class SafeLogAggregationInput(BaseModel):
    field: AggregationField
    query: str = Field(default="", max_length=500)
    service: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=SAFE_IDENTIFIER_PATTERN,
    )
    environment: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        pattern=SAFE_IDENTIFIER_PATTERN,
    )
    size: int = Field(default=10, ge=1, le=50)
