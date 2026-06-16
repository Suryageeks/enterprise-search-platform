from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agents.enterprise_agent_graph import enterprise_agent_graph
from langchain_core.messages import HumanMessage
from app.schemas.enterprise import EnterpriseAgentStreamRequest

router = APIRouter(
    prefix="/api/agents",
    tags=["Enterprise Agent"],
)

@router.post("/stream")
async def stream_enterprise_agent(request: EnterpriseAgentStreamRequest):
    async def event_generator():
        async for event in enterprise_agent_graph.astream_events(
            {
                "messages": [
                    HumanMessage(content=request.question)
                ]
            },
            version="v2"
        ):
            event_type = event.get("event")
            event_name = event.get("name")
            data = event.get("data", {})

            if event_type == "on_chat_model_stream":
                chunk = data.get("chunk")

                if chunk and chunk.content:
                    yield sse_event(
                        "token",
                        {
                            "text": normalize_chunk_content(chunk.content)
                        }
                    )
            
            elif event_type == "on_tool_start":
                yield sse_event(
                    "tool_start",
                    {
                        "tool": event_name
                    }
                )
            
            elif event_type == "on_tool_end":
                output = data.get("output")
                
                yield sse_event(
                    "tool_end",
                    {
                        "tool": event_name,
                        "output": str(output)
                    }
                )
        
        yield sse_event(
            "done",
            {
                "status": "complete"
            }
        )
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

def normalize_chunk_content(content) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))

        return "".join(parts)

    return str(content)
