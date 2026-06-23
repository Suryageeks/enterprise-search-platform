from __future__ import annotations

from langchain_core.tools import tool

from app.client.opensearch_client import opensearch_log_client
from app.core.config import settings
from app.schemas.logs import ParsedLogQuery
from app.schemas.execution import ToolErrorCode
from app.services.tool_result_service import execute_tool, tool_error


def _parse_basic_log_query(query: str, size: int) -> ParsedLogQuery:
    normalized_query = query.lower()

    status_code_min = None
    status_code_max = None
    level = None

    if "5xx" in normalized_query:
        status_code_min = 500
        status_code_max = 599

    if "4xx" in normalized_query:
        status_code_min = 400
        status_code_max = 499

    if any(word in normalized_query for word in ["error", "errors", "failed", "failure", "exception", "timeout"]):
        level = "ERROR"

    service = None
    for candidate in ["payment", "orders", "catalog", "gateway"]:
        if candidate in normalized_query:
            service = candidate
            break

    ignored_keywords = {
        "4xx",
        "5xx",
        "and",
        "are",
        "count",
        "error",
        "errors",
        "failure",
        "failures",
        "find",
        "for",
        "logs",
        "most",
        "show",
        "the",
        "which",
        "with",
    }
    keywords = [
        word
        for word in query.replace("?", " ").replace(",", " ").split()
        if len(word) > 2 and word.lower() not in ignored_keywords
    ]

    return ParsedLogQuery(
        service=service,
        level=level,
        status_code_min=status_code_min,
        status_code_max=status_code_max,
        keywords=keywords,
        size=size,
    )


@tool
async def search_logs_tool(query: str, size: int = 10) -> str:
    """
    Search normalized logs in OpenSearch.

    Use this when the user asks for specific log events,
    failures, traces, errors, exceptions, requests, or services.
    """

    if not query.strip():
        return tool_error(
            tool="search_logs_tool",
            code=ToolErrorCode.INVALID_TOOL_INPUT,
            message="Log search query cannot be empty",
        )

    size = max(1,min(size, settings.max_log_search_size))

    async def operation() -> dict:

        parsed_query = _parse_basic_log_query(query=query, size=size)

        result = await opensearch_log_client.search_logs(parsed_query=parsed_query)
        hits = result.get("hits", {}).get("hits", [])
        total = result.get("hits", {}).get("total", {})

        logs = []

        for hit in hits:
            item = hit.get("_source", {})
            logs.append(
                {
                    "timestamp": item.get("timestamp"),
                    "service": item.get("service"),
                    "level": item.get("level"),
                    "message": item.get("message"),
                    "trace_id": item.get("traceId"),
                    "request_id": item.get("requestId"),
                    "status_code": item.get("statusCode"),
                    "endpoint": item.get("endpoint"),
                    "exception_type": item.get("exceptionType"),
                }
            )

        if isinstance(total, dict):
            total_value = total.get("value", len(logs))
        else:
            total_value = total

        return {
            "total": total_value,
            "logs": logs,
        }

    return await execute_tool(
        tool="search_logs_tool",
        operation=operation,
        failure_code=ToolErrorCode.LOG_SEARCH_FAILED,
        failure_message="Unable to search logs",
    )


@tool
async def aggregate_logs_tool(field: str, query: str = "", size: int = 10) -> str:
    """
    Aggregate logs by a field.

    Use this when the user asks questions like:
    - errors by service
    - failures by endpoint
    - count by status code
    - top exception types
    """
    field_map = {
        "service": "service",
        "level": "level",
        "status_code": "statusCode",
        "statusCode": "statusCode",
        "endpoint": "endpoint",
        "exception_type": "exceptionType",
        "exceptionType": "exceptionType",
    }

    if field not in field_map:
        return tool_error(
            tool="aggregate_logs_tool",
            code=ToolErrorCode.INVALID_TOOL_INPUT,
            message=f"Unsupported aggregation field: {field}",
            details={"allowed_fields": sorted(field_map)},
        )

    size = max(1,min(size, settings.max_aggregation_size))
    opensearch_field = field_map.get(field, field)

    async def operation() -> dict:
        parsed_query = _parse_basic_log_query(query=query, size=1)

        result = await opensearch_log_client.client.search(
            index=settings.opensearch_index,
            body={
                "size": 0,
                "query": opensearch_log_client.build_query(parsed_query),
                "aggs": {
                    "by_field": {
                        "terms": {
                            "field": opensearch_field,
                            "size": size,
                        }
                    }
                },
            },
        )

        buckets = (
            result.get("aggregations", {})
            .get("by_field", {})
            .get("buckets", [])
        )

        return {
            "field": opensearch_field,
            "buckets": [
                {
                    "key": bucket.get("key"),
                    "count": bucket.get("doc_count", 0),
                }
                for bucket in buckets
            ],
        }

    return await execute_tool(
        tool="aggregate_logs_tool",
        operation=operation,
        failure_code=ToolErrorCode.LOG_AGGREGATION_FAILED,
        failure_message="Unable to aggregate logs",
    )
