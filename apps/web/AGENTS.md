<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Web App Plan

We are building a simple chat-first frontend for the Enterprise Search Platform.

## Stack

- Next.js 16 App Router
- React 19
- JavaScript, not TypeScript
- Tailwind CSS 4
- Biome for linting/formatting

Do not add TypeScript unless the project direction changes. Keep the first UI simple and avoid adding heavy state libraries or component systems until needed.

## First Goal

Build a quick chat interface that calls the backend Enterprise Agent:

```text
User message
 -> POST /api/agents/query
 -> render answer
 -> later render structured outputs
```

The backend response shape is expected to include:

```json
{
  "answer": "...",
  "tool_calls": [],
  "logs": [],
  "aggregations": [],
  "sources": [],
  "dashboard": null
}
```

## Initial Pages And Files

Prefer this structure:

```text
src/app/page.js
src/app/chat/page.js
src/components/chat/ChatWindow.js
src/components/chat/MessageBubble.js
src/lib/api.js
```

Start with `/chat` as the main working screen. The root page can redirect or link to `/chat`.

## UI Scope

First pass:

- message list
- text input
- send button
- loading state
- error state
- render assistant answer text

Later passes:

- logs evidence table
- aggregation cards/charts
- RAG sources panel
- dashboard renderer
- document upload page
- chat sessions/history
- auth-aware navigation

## Backend Integration

Use a small API helper in `src/lib/api.js`. The frontend should call the query-service/gateway endpoint configured by environment variable, for example:

```text
AGENT_API_URL=http://localhost:9080/api/agents/query
```

Keep the helper isolated so we can later switch from direct query-service calls to gateway calls without rewriting UI components.

## Development Rules

- Keep components small and plain JavaScript.
- Use client components only where interactivity is required.
- Avoid Redux or global state for the first version.
- Do not hide structured response fields; keep them in message state even if the UI only renders `answer` initially.
- Run `npm run lint` from `apps/web` after meaningful changes.
