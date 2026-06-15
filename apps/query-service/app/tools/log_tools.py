from __future__ import annotations

import json

from langchain_core.tools import tool

from app.client.opensearch_client import opensearch_log_client
from app.core.config import settings
from app.schemas.logs import ParsedLogQuery


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

    return json.dumps(
        {
            "total": total_value,
            "logs": logs,
        },
        default=str,
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
    opensearch_field = field_map.get(field, field)

    parsed_query = _parse_basic_log_query(query=query, size=1)

    body = {
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
    }

    result = await opensearch_log_client.client.search(
        index=settings.opensearch_index,
        body=body,
    )

    buckets = result.get("aggregations", {}).get("by_field", {}).get("buckets", [])

    return json.dumps(
        {
            "field": opensearch_field,
            "buckets": [
                {
                    "key": bucket.get("key"),
                    "count": bucket.get("doc_count", 0),
                }
                for bucket in buckets
            ],
        },
        default=str,
    )
