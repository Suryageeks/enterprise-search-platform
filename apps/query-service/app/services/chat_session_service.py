from datetime import datetime, timezone
from uuid import UUID
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession

class ChatSessionNotFoundError(Exception):
    pass

class ChatSessionService:
    async def create_session(
        self,
        db: AsyncSession, 
        title: str | None = None, 
        user_id: UUID | None = None
    ) -> ChatSession:
        session = ChatSession(
            title=title.strip() if title and title.strip() else "New chat",
            user_id=user_id
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)
    
        return session
    
    async def get_session(
        self,
        db: AsyncSession,
        session_id: UUID,
    ) -> ChatSession | None:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )

        return result.scalar_one_or_none()
    
    async def require_session(
        self,
        db: AsyncSession,
        session_id: UUID
    ) -> ChatSession:
        chat_session = await self.get_session(db, session_id)

        if chat_session is None:
            raise ChatSessionNotFoundError(
                f"Chat session {session_id} was not found"
            )
    
        return chat_session
    
    async def list_sessions(
        self,
        db: AsyncSession,
        *,
        limit: int = 50,
        offset: int = 0
    ) -> list[ChatSession]:
        result = await db.execute(
            select(ChatSession)
            .order_by(
                desc(ChatSession.updated_at),
                desc(ChatSession.id),
            )
            .limit(limit)
            .offset(offset)
        )

        return list(result.scalars().all())
    
    async def rename_session(
        self,
        db: AsyncSession,
        session_id: UUID,
        title: str
    ) -> ChatSession:
        chat_session = await self.require_session(db, session_id)

        chat_session.title = self._normalize_title(title)
        chat_session.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(chat_session)

        return chat_session
    
    async def delete_session(
        self,
        db: AsyncSession,
        session_id: UUID,
    ) -> None:
        chat_session = await self.require_session(db, session_id)

        await db.delete(chat_session)
        await db.commit()
    
    async def list_messages(
        self,
        db: AsyncSession,
        session_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ChatMessage]:
        
        await self.require_session(db, session_id)

        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .limit(limit)
            .offset(offset)
        )

        return list(result.scalars().all())
    
    async def add_message(
        self,
        db: AsyncSession,
        session_id: UUID,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> ChatMessage:
        session = await self.require_session(db, session_id)
        
        clean_content = content.strip()

        if not clean_content:
            raise ValueError("Message content cannot be empty")

        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=clean_content,
            message_metadata=metadata or {}
        )

        db.add(message)

        if session.title == "New chat" and role == "user":
            session.title = self._generate_title(clean_content)

        session.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(message)
        await db.refresh(session)

        return message

    def _generate_title(self, content: str) -> str:
        clean = " ".join(content.strip().split())

        if not clean:
            return "New chat"
        
        return clean[:60]
    
    def _normalize_title(self, title: str | None) -> str:
        if title is None:
            return "New chat"

        clean = " ".join(title.strip().split())

        return clean[:255] if clean else "New chat"


chat_session_service = ChatSessionService()
