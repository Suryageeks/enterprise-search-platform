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
    
    if data.get("used_context"):
        return True
    
    buckets = data.get("buckets")

    if isinstance(buckets, list) and buckets:
        return True
    
    return False

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



    
