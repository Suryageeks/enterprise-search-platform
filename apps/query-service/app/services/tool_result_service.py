import json
import logging
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any

from app.schemas.execution import (
    ToolError,
    ToolErrorCode,
    ToolExecutionStatus,
    ToolResult,
    AgentExecutionStatus
)

logger = logging.getLogger(__name__)

def tool_success(
    *,
    tool: str,
    data: dict[str, Any],
    duration_ms: int | None = None
) -> str:
    result = ToolResult(
        tool=tool,
        status=ToolExecutionStatus.SUCCESS,
        data=data,
        duration_ms=duration_ms
    )

    return result.model_dump_json()


def tool_error(
    *,
    tool: str,
    code: ToolErrorCode,
    message: str,
    retryable: bool = False,
    details: dict[str, Any] | None = None,
    duration_ms: int | None = None
) -> str:
    result = ToolResult(
        tool=tool,
        status=ToolExecutionStatus.ERROR,
        error=ToolError(
            code=code,
            message=message,
            retryable=retryable,
            details=details or {}
        ),
        duration_ms=duration_ms
    )

    return result.model_dump_json()

async def execute_tool(
    *,
    tool: str,
    operation: Callable[[], Awaitable[dict[str, Any]]],
    failure_code: ToolErrorCode,
    failure_message: str
) -> str:
    started_at = perf_counter()

    try:
        data = await operation()

        return tool_success(
            tool=tool,
            data=data,
            duration_ms=int((perf_counter() - started_at)*1000)
        )
    except Exception as exc:
        logger.exception("%s failed", tool)

        return tool_error(
            tool=tool,
            code=failure_code,
            message=failure_message,
            retryable=True,
            details={"exception_type": type(exc).__name__},
            duration_ms=int((perf_counter() - started_at) * 1000),
        )

def parse_tool_result(raw: str) -> ToolResult | None:
    try:
        data = json.loads(raw)
        return ToolResult.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        return None

def calculate_agent_status(tool_results: list[ToolResult]) -> AgentExecutionStatus:
    if not tool_results:
        return AgentExecutionStatus.SUCCESS
    
    successful = sum(
        result.status == ToolExecutionStatus.SUCCESS
        for result in tool_results
    )

    failed = sum(
        result.status == ToolExecutionStatus.ERROR
        for result in tool_results
    )

    if successful and failed:
        return AgentExecutionStatus.PARTIAL
    
    if failed and not successful:
        return AgentExecutionStatus.ERROR
    
    return AgentExecutionStatus.SUCCESS

def build_warnings(tool_results: list[ToolResult]) -> list[str]:
    return [
        f"{result.tool}: {result.error.message}"
        for result in tool_results
        if result.error is not None
    ]
