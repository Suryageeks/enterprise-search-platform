# Chat Sessions, Memory, and Agent Reliability Plan

## Project Status

Last updated: 2026-06-23

The platform currently has the main RAG and multi-agent execution path in place.
The active backend phase is structured tool results, error handling, and partial
result support.

| Phase | Status | Notes |
| --- | --- | --- |
| Platform data services | Complete | Postgres, OpenSearch, Qdrant, Redis, and mock OpenSearch data are available through Docker. |
| LangChain RAG | Complete for MVP | BERT embeddings, Qdrant retrieval, and Gemini/Ollama-backed answer generation are implemented. |
| LangGraph enterprise agent | Complete for MVP | The agent can select and call log search, aggregation, RAG, and dashboard tools. |
| Dashboard agent and execution | Complete for MVP | Dashboard specifications can be generated and executed against OpenSearch. |
| Streaming and frontend integration | Complete for MVP | SSE responses, tool activity, Markdown rendering, and the chat interface are integrated. |
| Chat sessions | Complete | Postgres-backed sessions, messages, CRUD APIs, and session query endpoints are implemented. |
| LangGraph short-term memory | Complete | The Postgres checkpointer uses `chat_session_id` as `thread_id` for follow-up context. |
| MLflow observability | Complete for MVP | LangChain/LangGraph traces can be inspected in the local MLflow service. |
| Structured tool results and partial errors | In progress | Core Pydantic schemas and result helpers exist, but all four tools and API/SSE output paths still need to use and validate the contract. |
| Long-term memory | Not started | Semantic and procedural memory will use Qdrant and background extraction. |
| Semantic cache | Not started | Cache repeated or semantically equivalent requests after correctness and invalidation rules are defined. |
| Evaluation and production hardening | Deferred | DeepEval/evaluation datasets, load tests, security, retries, limits, and deployment hardening remain. |

This document describes the next memory layer we will add to the Enterprise Search Platform.

The immediate goal is to support real chat sessions and short-term conversation memory so users can ask follow-up questions naturally.

## Current Direction

We will use a hybrid approach:

- Postgres application tables for product-facing chat history.
- LangGraph Postgres checkpointer for short-term agent memory.

These solve different problems and should both exist.

## Phase 1: Chat Sessions - Complete

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

## Phase 2: Short-Term Memory - Complete

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

## Phase 3: Structured Tool Results and Partial Errors - In Progress

This phase makes failures predictable for the agent, API, frontend, and
observability layer. Tool output remains structured JSON. Markdown is only used
inside the human-readable `answer` field.

The common contract contains:

- `ToolResult` with `success` or `error` status.
- Stable error codes and retryability metadata.
- Tool duration for diagnostics.
- `AgentResult` with `success`, `partial`, or `error` status.
- Successful evidence even when another tool fails.
- Warnings suitable for API and frontend display.

Implementation approach:

- Pydantic for `ToolResult`, `ToolError`, and `AgentResult`.
- LangChain `@tool` definitions for the four enterprise tools.
- LangGraph `ToolNode` for tool execution and routing.
- Shared exception handling around each tool operation.
- Timeouts and retries are intentionally deferred until baseline behavior is stable.

Remaining work in this phase:

1. Correct and test the shared result helper.
2. Apply the contract to log search and log aggregation.
3. Apply the contract to RAG search and dashboard generation/execution.
4. Parse structured tool messages in the enterprise graph.
5. Return `status`, `tool_results`, and `warnings` from normal and SSE APIs.
6. Store JSON-serializable result metadata in `chat_messages`.
7. Test success, mixed-success, and total-failure scenarios.

## Phase 4: Long-Term Memory - Not Started

Use Qdrant for durable semantic and procedural memories. Extraction and writes
run after the response so they do not increase chat latency.

- Semantic memory stores durable user, team, service, and incident facts.
- Procedural memory stores reusable investigation workflows.
- Retrieval must be scoped by tenant/user and memory type.
- Every memory needs provenance, confidence, timestamps, and invalidation rules.

## Phase 5: Conversation Summaries and Context Management - Not Started

Add token-aware summaries when long conversations approach the model context
budget. Recent raw messages remain in STM while older context is represented by
a summary with links to persisted chat history.

## Phase 6: Semantic Cache - Not Started

Use Qdrant or a dedicated cache index to find semantically equivalent requests.
Cache keys must include filters, tenant, data time range, tool/schema version,
and model configuration. Time-sensitive log investigations should use short TTLs
or bypass the cache.

## Phase 7: Evaluation and Production Hardening - Deferred

- Create golden investigation datasets and expected tool-call sequences.
- Evaluate retrieval relevance, answer faithfulness, and tool selection.
- Add integration tests for Postgres, OpenSearch, Qdrant, Gemini, and Ollama.
- Test concurrency, streaming cancellation, retries, and rate limits.
- Add authentication, tenant isolation, secrets management, and audit controls.

## Deferred Features

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

## Updated Build Order

1. Finish structured tool results, errors, timeouts, and partial responses.
2. Add semantic long-term memory in Qdrant using background extraction.
3. Add procedural memory with explicit review and versioning.
4. Add conversation summarization and context-budget management.
5. Add semantic caching with strict scoping and invalidation.
6. Build evaluation datasets and automated agent tests.
7. Complete production security, resilience, and deployment hardening.
