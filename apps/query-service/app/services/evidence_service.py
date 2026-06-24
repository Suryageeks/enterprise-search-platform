from typing import Any

from langchain_core.messages import (
    BaseMessage,
    ToolMessage,
)

from app.schemas.execution import (
    ToolExecutionStatus,
    ToolResult,
)
from app.services.tool_result_service import (
    parse_tool_result,
)

def tool_result_has_evidence(
    result: ToolResult,
) -> bool:
    if(result.status != ToolExecutionStatus.SUCCESS or not result.data):
        return False
    
    data = result.data

    if data.get("logs"):
        return True
    
    if data.get("sources"):
        return True
    
    if data.get("dashboard"):
        return True
    
    buckets = data.get("buckets")

    if isinstance(buckets, list) and buckets:
        return True
    
    return False


def collect_evidence(
    messages: list[BaseMessage],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    counters = {
        "log": 0,
        "source": 0,
        "aggregation": 0,
    }

    for message in messages:
        if not isinstance(message, ToolMessage):
            continue

        result = parse_tool_result(str(message.content))
        if (
            result is None
            or result.status != ToolExecutionStatus.SUCCESS
            or not result.data
        ):
            continue

        data = result.data

        for log in data.get("logs", [])[:20]:
            counters["log"] += 1
            evidence.append(
                {
                    "id": f"log-{counters['log']}",
                    "type": "log",
                    "timestamp": log.get("timestamp"),
                    "service": log.get("service"),
                    "level": log.get("level"),
                    "message": str(log.get("message") or "")[:1000],
                    "trace_id": log.get("trace_id"),
                    "request_id": log.get("request_id"),
                    "status_code": log.get("status_code"),
                    "endpoint": log.get("endpoint"),
                    "exception_type": log.get("exception_type"),
                }
            )

        for source in data.get("sources", [])[:10]:
            counters["source"] += 1
            evidence.append(
                {
                    "id": f"source-{counters['source']}",
                    "type": "document",
                    "doc_id": source.get("doc_id"),
                    "file_name": source.get("file_name"),
                    "score": source.get("score"),
                    "text_preview": str(
                        source.get("text_preview") or ""
                    )[:1500],
                }
            )

        buckets = data.get("buckets", [])
        if buckets:
            counters["aggregation"] += 1
            evidence.append(
                {
                    "id": f"aggregation-{counters['aggregation']}",
                    "type": "aggregation",
                    "field": data.get("field"),
                    "buckets": buckets[:20],
                }
            )

    return evidence

def messages_have_evidence(
    messages: list[BaseMessage],
) -> bool:
    
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue

        result = parse_tool_result(
            str(message.content)
        )

        if (result is not None and tool_result_has_evidence(result)):
            return True
        
    return False



    
