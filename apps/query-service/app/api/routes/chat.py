from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.chat import (
    ChatMessageResponse,
    ChatSessionResponse,
    CreateChatSessionRequest,
    UpdateChatSessionRequest,
)
from app.services.chat_session_service import (
    chat_session_service,
    ChatSessionNotFoundError
)
from app.agents.enterprise_agent_graph import (
    delete_enterprise_agent_thread,
    run_enterprise_agent,
)
from app.schemas.chat import ChatQueryRequest, ChatQueryResponse

router = APIRouter(prefix="/api/chat", tags=["Chat"])

def not_found_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Chat session not found",
    )

@router.post("/sessions", 
            response_model=ChatSessionResponse,
            status_code=status.HTTP_201_CREATED,
)
async def create_session(
    request: CreateChatSessionRequest,
    db: AsyncSession = Depends(get_db_session)
):
    return await chat_session_service.create_session(
        db=db,
        title=request.title
    )

@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    limit: int = Query(default=50, ge=1,le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
):
    return await chat_session_service.list_sessions(
        db=db,
        limit=limit,
        offset=offset
    )

@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    session = await chat_session_service.get_session(
        db=db,
        session_id=session_id
    )

    if session is None:
        raise not_found_error()

    return session

@router.patch(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse
)
async def rename_session(
    session_id: UUID,
    request: UpdateChatSessionRequest,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await chat_session_service.rename_session(
            db=db,
            session_id=session_id,
            title=request.title
        )
    except ChatSessionNotFoundError as exc:
        raise not_found_error() from exc

@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT
)  
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    try:
        await chat_session_service.require_session(
            db=db,
            session_id=session_id,
        )
        await delete_enterprise_agent_thread(str(session_id))
        await chat_session_service.delete_session(
            db=db,
            session_id=session_id
        )
    except ChatSessionNotFoundError as exc:
        raise not_found_error() from exc
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[ChatMessageResponse],
)
async def list_messages(
    session_id: UUID,
    limit: int = Query(default=50, ge=1,le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    try:
        return await chat_session_service.list_messages(
            db=db,
            session_id=session_id,
            limit=limit,
            offset=offset
        )
    except ChatSessionNotFoundError as exc:
        raise not_found_error() from exc

@router.post(
    "/sessions/{session_id}/query",
    response_model=ChatQueryResponse,
)
async def query_session(
    session_id: UUID,
    request: ChatQueryRequest,
    db: AsyncSession = Depends(get_db_session),
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

    result = await run_enterprise_agent(
        question=question,
        thread_id=str(session_id)
    )

    metadata = {
        "status": result["status"],
        "tool_calls": result.get("tool_calls", []),
        "tool_results": result.get("tool_results", []),
        "warnings": result.get("warnings", []),
        "logs": result.get("logs", []),
        "aggregations": result.get("aggregations", []),
        "sources": result.get("sources", []),
        "dashboard": result.get("dashboard"),
        "remediation": result.get("remediation"),
    }

    await chat_session_service.add_message(
        db=db,
        session_id=session_id,
        role="assistant",
        content=result["answer"],
        metadata=metadata
    )

    return ChatQueryResponse(
        session_id=session_id,
        answer=result["answer"],
        **metadata,
    )
