# Chat Sessions and Memory Plan

This document describes the next memory layer we will add to the Enterprise Search Platform.

The immediate goal is to support real chat sessions and short-term conversation memory so users can ask follow-up questions naturally.

## Current Direction

We will use a hybrid approach:

- Postgres application tables for product-facing chat history.
- LangGraph Postgres checkpointer for short-term agent memory.

These solve different problems and should both exist.

## Phase 1: Chat Sessions

Chat sessions are for the frontend and product experience.

We will add:

- `chat_sessions`
- `chat_messages`

These tables will support:

- Creating a new chat.
- Listing chats in the sidebar.
- Loading previous messages.
- Saving user messages.
- Saving assistant messages.
- Storing response metadata such as tool calls, logs, sources, aggregations, and dashboards.

The frontend should use these APIs instead of mock/local-only sessions.

## Phase 2: Short-Term Memory

Short-term memory is for active conversation context.

We will use LangGraph's Postgres checkpointer with:

```text
thread_id = chat_session_id
```

This lets the enterprise agent remember prior messages and tool results inside a conversation.

Example:

```text
User: Show payment timeout errors.
Assistant: Found payment timeout logs.
User: Group them by endpoint.
```

The second question should work because LangGraph can load the prior state for the same `thread_id`.

Short-term memory will be written on the hot path because the next user message depends on it immediately.

## Request Flow

```text
User sends message
 -> create or load chat_session
 -> save user message in chat_messages
 -> run LangGraph with thread_id = session_id
 -> LangGraph loads short-term memory automatically
 -> tools run if needed
 -> assistant answer is generated
 -> save assistant message in chat_messages
 -> return response to frontend
```

## Packages To Add

```text
sqlalchemy[asyncio]
asyncpg
langgraph-checkpoint-postgres
psycopg[binary,pool]
```

SQLAlchemy/asyncpg will be used for application tables.

Psycopg will be used by the LangGraph Postgres checkpointer.

## Configuration

We will keep separate database URLs because the app database layer and LangGraph checkpointer use different drivers.

Local:

```env
DATABASE_URL=postgresql+asyncpg://enterprise_user:enterprise_pass@localhost:5432/enterprise_search
LANGGRAPH_CHECKPOINT_URL=postgresql://enterprise_user:enterprise_pass@localhost:5432/enterprise_search
```

Docker:

```env
DATABASE_URL=postgresql+asyncpg://enterprise_user:enterprise_pass@postgres:5432/enterprise_search
LANGGRAPH_CHECKPOINT_URL=postgresql://enterprise_user:enterprise_pass@postgres:5432/enterprise_search
```

## What We Are Not Adding Yet

The following should come later, after chat sessions and short-term memory are stable:

- Semantic cache.
- Long-term memory.
- Procedural memory.
- Memory extraction background jobs.
- Conversation summaries.
- Pinned context.
- Memory management UI.

## Later Memory Direction

After short-term memory, we will add long-term memory in the background path.

Long-term memory should not slow down the chat response.

Planned long-term memory types:

- Semantic memory: durable facts, preferences, recurring service context, incident learnings.
- Procedural memory: reusable investigation workflows and agent behavior patterns.

Semantic memory examples:

```text
User usually investigates payment service.
Production is the default environment for this team.
User prefers endpoint-level dashboards.
```

Procedural memory examples:

```text
For 5xx incidents, search recent ERROR logs, aggregate by endpoint, check exceptionType, then search runbooks.
For payment timeout incidents, check database timeout logs and connection pool runbooks.
```

Long-term memory writes should happen in a background job after the response is complete.

## Recommended Build Order

1. Add chat session database tables.
2. Add chat session service and APIs.
3. Add LangGraph Postgres checkpointer.
4. Use `session_id` as LangGraph `thread_id`.
5. Save user and assistant messages for UI history.
6. Update frontend to load real sessions/messages.
7. Add semantic and procedural long-term memory later.

