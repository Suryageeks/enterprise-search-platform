from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession


from app.agents.enterprise_agent_graph import (
    extract_message_text,
    extract_structured_outputs,
    get_enterprise_agent_graph,
    messages_from_current_turn,
)
from app.db.session import AsyncSessionLocal, get_db_session
from app.schemas.chat import ChatStreamRequest
from app.schemas.enterprise import EnterpriseAgentStreamRequest
from app.services.chat_session_service import (
    ChatSessionNotFoundError,
    chat_session_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Enterprise Agent"])


def not_found_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Chat session not found",
    )

@router.post("/api/agents/stream")
async def stream_enterprise_agent(request: EnterpriseAgentStreamRequest):
    return build_streaming_response(
        question=request.question.strip(),
        thread_id=f"legacy-{uuid4()}",
        session_id=None,
        persist_assistant=False,
    )

@router.post("/api/chat/sessions/{session_id}/stream")
async def stream_chat_session(
    session_id: UUID,
    request: ChatStreamRequest,
    db: AsyncSession = Depends(get_db_session)
):
    try:
        await chat_session_service.require_session(
            db=db,
            session_id=session_id
        )

    except ChatSessionNotFoundError as exc:
        raise not_found_error() from exc
    
    question = request.query.strip()

    await chat_session_service.add_message(
        db=db,
        session_id=session_id,
        role="user",
        content=question
    )

    return build_streaming_response(
        question=question,
        thread_id=str(session_id),
        session_id=session_id,
        persist_assistant=True
    )

def sse_event(event: str, data: dict) -> str:
    return (
        f"event: {event}\n"
        f"data: {json.dumps(data, default=str, ensure_ascii=False)}\n\n"
    )


def normalize_chunk_content(content) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []

        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")

                if isinstance(text, str):
                    parts.append(text)

        return "".join(parts)

    return ""


def normalize_tool_output(output) -> str:
    if output is None:
        return ""

    content = getattr(output, "content", output)

    if isinstance(content, str):
        return content

    return json.dumps(content, default=str)

def build_streaming_response(
    *,
    question: str,
    thread_id: str,
    session_id: UUID | None,
    persist_assistant: bool
) -> StreamingResponse:
    current_message = HumanMessage(
        id=str(uuid4()),
        content=question
    )

    graph_config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    return StreamingResponse(
        stream_agent_events(
            current_message=current_message,
            graph_config=graph_config,
            session_id=session_id,
            persist_assistant=persist_assistant
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

async def stream_agent_events(
    *,
    current_message: HumanMessage,
    graph_config: dict,
    session_id: UUID | None,
    persist_assistant: bool,
) -> AsyncIterator[str]:
    
    compiled_graph = get_enterprise_agent_graph()

    try:
        async for event in compiled_graph.astream_events(
            {
                "messages": [current_message]
            },
            config=graph_config,
            version="v2"
        ):
            event_type = event.get("event")
            event_name = event.get("name")
            data = event.get("data", {})

            if event_type == "on_chat_model_stream":
                chunk = data.get("chunk")
                text = normalize_chunk_content(
                    getattr(chunk,"content","")
                )

                if text:
                    yield sse_event(
                        "token",
                        {
                            "text": text
                        }
                    )
            
            elif event_type == "on_tool_start":
                yield sse_event(
                    "tool_start",
                    {
                        "tool": event_name or "unknown_tool"
                    }
                )
            
            elif event_type == "on_tool_end":
                yield sse_event(
                    "tool_end",
                    {
                        "tool": event_name or "unknown_tool",
                        "output": normalize_tool_output(
                            data.get("output")
                        )
                    }
                )
        
        snapshot = await compiled_graph.aget_state(graph_config)
        all_messages = snapshot.values.get("messages",[])

        turn_messages = messages_from_current_turn(
            messages=all_messages,
            current_message_id=current_message.id,
        )

        final_message = turn_messages[-1]
        answer = extract_message_text(final_message.content)
        structured = extract_structured_outputs(turn_messages)

        if persist_assistant and session_id is not None:
            async with AsyncSessionLocal() as db:
                await chat_session_service.add_message(
                    db=db,
                    session_id=session_id,
                    role="assistant",
                    content=answer,
                    metadata=structured,
                )
        
        yield sse_event(
            "done",
            {
                "status": "complete",
                "session_id": (
                    str(session_id)
                    if session_id is not None else None
                ),
                "answer": answer,
                **structured
            }
        )

    except asyncio.CancelledError:
        logger.info(
            "Agent stream disconnected for thread %s",
            graph_config["configurable"]["thread_id"],
        )
        raise

    except Exception:
        logger.exception(
            "Agent stream failed for thread %s",
            graph_config["configurable"]["thread_id"],
        )
    
        yield sse_event(
            "error",
            {
                "detail": "Agent stream failed",
                "session_id": (
                    str(session_id)
                    if session_id is not None
                    else None
                ),
            }
        )
