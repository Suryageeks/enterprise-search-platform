"use client";

import { useEffect, useRef, useState } from "react";
import {
  createChatSession,
  deleteChatSession,
  listChatMessages,
  listChatSessions,
  normalizeAgentResult,
  renameChatSession,
} from "@/lib/api";
import { streamEnterpriseAgent } from "@/lib/streamAgent";
import MessageBubble from "./MessageBubble";

const PROMPTS = [
  "Find payment 5xx errors",
  "Create dashboard by service",
  "Check database timeout runbooks",
  "Show top services with errors",
];

function createMessageId() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export default function ChatWindow() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const [activeTools, setActiveTools] = useState([]);
  const [isLoadingSession, setIsLoadingSession] = useState(true);
  const textareaRef = useRef(null);

  const canSend =
    input.trim().length > 0 &&
    !isSending &&
    !isLoadingSession &&
    Boolean(activeSessionId);
  const hasConversation = messages.length > 0;
  const activeSession = sessions.find(
    (session) => session.id === activeSessionId,
  );
  useEffect(() => {
    let cancelled = false;

    async function initializeSessions() {
      try {
        let availableSessions = await listChatSessions();

        if (!availableSessions.length) {
          availableSessions = [await createChatSession()];
        }

        const initialSession = availableSessions[0];
        const persistedMessages = await listChatMessages(initialSession.id);

        if (cancelled) {
          return;
        }

        setSessions(availableSessions);
        setActiveSessionId(initialSession.id);
        setMessages(persistedMessages);
      } catch (requestError) {
        if (!cancelled) {
          setError(getErrorMessage(requestError));
        }
      } finally {
        if (!cancelled) {
          setIsLoadingSession(false);
        }
      }
    }

    initializeSessions();

    return () => {
      cancelled = true;
    };
  }, []);

  async function sendMessage(text) {
    const question = text.trim();

    if (!question || isSending || !activeSessionId) {
      return;
    }

    setMessages((current) => [
      ...current,
      {
        id: createMessageId(),
        role: "user",
        content: question,
      },
    ]);
    setInput("");
    setError("");
    setActiveTools([]);
    setIsSending(true);

    let assistantMessageId = null;

    try {
      assistantMessageId = createMessageId();

      setMessages((current) => [
        ...current,
        {
          id: assistantMessageId,
          role: "assistant",
          content: "",
          data: {
            status: "pending",
            tool_calls: [],
            tool_results: [],
            warnings: [],
            logs: [],
            aggregations: [],
            sources: [],
            dashboard: null,
            remediation: null,
          },
        },
      ]);

      await streamEnterpriseAgent(activeSessionId, question, {
        onToken: (token) => {
          if (!token) {
            return;
          }

          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessageId
                ? {
                    ...message,
                    content: `${message.content}${token}`,
                  }
                : message,
            ),
          );
        },
        onToolStart: (tool) => {
          setActiveTools((current) => upsertTool(current, tool, "running"));
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessageId
                ? {
                    ...message,
                    data: {
                      ...message.data,
                      tool_calls: uniqueList([
                        ...(message.data?.tool_calls || []),
                        tool,
                      ]),
                    },
                  }
                : message,
            ),
          );
        },
        onToolEnd: (tool, result) => {
          setActiveTools((current) => upsertTool(current, tool, "done"));
          if (!result) {
            return;
          }

          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessageId
                ? {
                    ...message,
                    data: {
                      ...message.data,
                      tool_results: [
                        ...(message.data?.tool_results || []),
                        result,
                      ],
                    },
                  }
                : message,
            ),
          );
        },
        onDone: (payload) => {
          const result = normalizeAgentResult(payload);

          setMessages((current) =>
            current.map((message) =>
              message.id === assistantMessageId
                ? {
                    ...message,
                    content:
                      result.answer ||
                      "The agent completed the request without an answer.",
                    data: result,
                  }
                : message,
            ),
          );
          setActiveTools((current) =>
            current.map((tool) => ({ ...tool, status: "done" })),
          );
          refreshSessions();
        },
      });
    } catch (requestError) {
      const failureMessage = getErrorMessage(requestError);
      setError(failureMessage);
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantMessageId
            ? {
                ...message,
                content: `I could not complete that request. ${failureMessage}`,
                data: null,
              }
            : message,
        ),
      );
    } finally {
      setIsSending(false);
      requestAnimationFrame(() => textareaRef.current?.focus());
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    sendMessage(input);
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage(input);
    }
  }

  async function refreshSessions() {
    try {
      setSessions(await listChatSessions());
    } catch {
      // The active conversation remains usable if the sidebar refresh fails.
    }
  }

  async function handleNewChat() {
    if (isSending) {
      return;
    }

    setIsLoadingSession(true);
    setError("");

    try {
      const session = await createChatSession();
      setSessions((current) => [
        session,
        ...current.filter((item) => item.id !== session.id),
      ]);
      setActiveSessionId(session.id);
      setMessages([]);
      setActiveTools([]);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsLoadingSession(false);
    }
  }

  async function handleSelectSession(sessionId) {
    if (isSending || sessionId === activeSessionId) {
      return;
    }

    setIsLoadingSession(true);
    setError("");

    try {
      const persistedMessages = await listChatMessages(sessionId);
      setActiveSessionId(sessionId);
      setMessages(persistedMessages);
      setActiveTools([]);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsLoadingSession(false);
    }
  }

  async function handleRenameSession(session) {
    const title = window.prompt("Rename chat", session.title);

    if (!title?.trim() || title.trim() === session.title) {
      return;
    }

    try {
      const updated = await renameChatSession(session.id, title.trim());
      setSessions((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    }
  }

  async function handleDeleteSession(sessionId) {
    if (isSending || !window.confirm("Delete this chat?")) {
      return;
    }

    try {
      await deleteChatSession(sessionId);
      let remaining = sessions.filter((session) => session.id !== sessionId);

      if (!remaining.length) {
        remaining = [await createChatSession()];
      }

      setSessions(remaining);

      if (sessionId === activeSessionId) {
        const nextSession = remaining[0];
        setActiveSessionId(nextSession.id);
        setMessages(await listChatMessages(nextSession.id));
        setActiveTools([]);
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    }
  }

  return (
    <main className="h-screen overflow-hidden bg-white text-[#101010]">
      <div className="grid h-screen grid-cols-1 overflow-hidden lg:grid-cols-[280px_1fr]">
        <Sidebar
          activeSessionId={activeSessionId}
          isSending={isSending}
          onDeleteSession={handleDeleteSession}
          onNewChat={handleNewChat}
          onPrompt={sendMessage}
          onRenameSession={handleRenameSession}
          onSelectSession={handleSelectSession}
          sessions={sessions}
        />

        <section className="relative flex h-screen min-h-0 flex-col overflow-hidden">
          <TopBar title={activeSession?.title} />

          <div className="min-h-0 flex-1 scroll-smooth overflow-y-auto overscroll-contain px-4 pb-56 pt-8">
            <div className="mx-auto max-w-[860px]">
              {isLoadingSession
                ? <div className="py-20 text-center text-sm text-[#777]">
                    Loading conversation...
                  </div>
                : hasConversation
                  ? <Conversation
                      activeTools={activeTools}
                      messages={messages}
                      isSending={isSending}
                    />
                  : <EmptyState onPrompt={sendMessage} isSending={isSending} />}
            </div>
          </div>

          <Composer
            canSend={canSend}
            error={error}
            input={input}
            isSending={isSending}
            onChange={setInput}
            onKeyDown={handleKeyDown}
            onSubmit={handleSubmit}
            textareaRef={textareaRef}
          />
        </section>
      </div>
    </main>
  );
}

function upsertTool(tools, name, status) {
  const existing = tools.find((tool) => tool.name === name);

  if (existing) {
    return tools.map((tool) =>
      tool.name === name ? { ...tool, status } : tool,
    );
  }

  return [...tools, { name, status }];
}

function uniqueList(items) {
  return [...new Set(items)];
}

function getErrorMessage(error) {
  return error instanceof Error
    ? error.message
    : "Unable to reach the chat service.";
}

function groupSessions(sessions) {
  const groups = {};
  const now = new Date();
  const today = startOfDay(now);
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const previousThirtyDays = new Date(today);
  previousThirtyDays.setDate(previousThirtyDays.getDate() - 30);

  for (const session of sessions) {
    const updatedAt = new Date(session.updated_at || session.created_at);
    let section = "Older";

    if (updatedAt >= today) {
      section = "Today";
    } else if (updatedAt >= yesterday) {
      section = "Yesterday";
    } else if (updatedAt >= previousThirtyDays) {
      section = "Previous 30 Days";
    }

    groups[section] ||= [];
    groups[section].push(session);
  }

  return groups;
}

function startOfDay(value) {
  const result = new Date(value);
  result.setHours(0, 0, 0, 0);
  return result;
}

function Sidebar({
  activeSessionId,
  isSending,
  onDeleteSession,
  onNewChat,
  onPrompt,
  onRenameSession,
  onSelectSession,
  sessions,
}) {
  const groupedSessions = groupSessions(sessions);

  return (
    <aside className="hidden h-screen min-h-0 overflow-hidden bg-[#f7f7f7] px-3 py-3 lg:flex lg:flex-col">
      <div className="shrink-0">
        <div className="flex h-10 items-center justify-between px-1">
          <div className="flex items-center gap-2.5">
            <span className="grid h-8 w-8 place-items-center rounded-full bg-black text-[11px] font-semibold text-white">
              LG
            </span>
            <span className="text-[16px] font-semibold tracking-[-0.02em]">
              LogGPT
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              className="h-8 rounded-lg px-2 text-xs font-medium text-[#555] hover:bg-[#ececec]"
              aria-label="Search"
            >
              Search
            </button>
            <button
              type="button"
              onClick={onNewChat}
              disabled={isSending}
              className="grid h-8 w-8 place-items-center rounded-lg text-lg text-[#555] hover:bg-[#ececec]"
              aria-label="New chat"
            >
              +
            </button>
          </div>
        </div>

        <div className="mt-5 space-y-1">
          {["LogGPT", "Log Analyst", "Dashboard Builder", "RAG Search"].map(
            (item, index) => (
              <button
                key={item}
                type="button"
                onClick={() => onPrompt(item)}
                disabled={isSending}
                className={`flex h-9 w-full items-center gap-2.5 rounded-lg px-2.5 text-left text-[14px] transition hover:bg-[#eeeeee] disabled:opacity-60 ${
                  index === 0 ? "bg-[#eeeeee]" : ""
                }`}
              >
                <span
                  className={`h-5 w-5 rounded-full ${
                    index === 0 ? "bg-black" : "bg-[#d8d8d8]"
                  }`}
                />
                {item}
              </button>
            ),
          )}
        </div>
      </div>

      <nav className="mt-6 flex-1 overflow-y-auto px-1 pb-4">
        {Object.entries(groupedSessions).map(([section, items]) => (
          <div key={section} className="mb-7">
            <div className="mb-2 px-2 text-sm font-semibold">{section}</div>
            <div className="space-y-0.5">
              {items.map((session) => (
                <div
                  key={session.id}
                  className={`group flex items-center rounded-lg pr-1 ${
                    activeSessionId === session.id ? "bg-[#eeeeee]" : ""
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => onSelectSession(session.id)}
                    disabled={isSending}
                    className="h-9 min-w-0 flex-1 truncate px-2 text-left text-[14px] transition disabled:opacity-60"
                    title={session.title}
                  >
                    {session.title}
                  </button>
                  <button
                    type="button"
                    onClick={() => onRenameSession(session)}
                    disabled={isSending}
                    className="hidden h-7 px-1 text-[11px] text-[#666] hover:text-black group-hover:block"
                    aria-label={`Rename ${session.title}`}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => onDeleteSession(session.id)}
                    disabled={isSending}
                    className="hidden h-7 px-1 text-base text-[#777] hover:text-black group-hover:block"
                    aria-label={`Delete ${session.title}`}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="shrink-0 border-t border-black/5 pt-3">
        <button
          type="button"
          onClick={onNewChat}
          disabled={isSending}
          className="mb-1 flex w-full items-center gap-3 rounded-2xl bg-[#eeeeee] p-3 text-left"
        >
          <span className="grid h-9 w-9 place-items-center rounded-full bg-white text-lg">
            +
          </span>
          <span>
            <span className="block text-sm font-semibold">New workspace</span>
            <span className="block text-xs text-[#777]">
              Add logs and documents
            </span>
          </span>
        </button>
      </div>
    </aside>
  );
}

function TopBar({ title }) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between px-5">
      <button type="button" className="text-[17px] font-medium">
        {title || "LogGPT"} <span className="text-[#777]">⌄</span>
      </button>
      <div className="h-8 w-8 rounded-full bg-gradient-to-br from-[#e6d7c8] to-[#1f2937]" />
    </header>
  );
}

function EmptyState({ onPrompt, isSending }) {
  return (
    <div className="flex min-h-[calc(100vh-15rem)] flex-col items-center justify-center text-center">
      <div className="h-20 w-20 rounded-full bg-gradient-to-br from-[#e1e1e1] via-[#cfcfcf] to-[#222]" />
      <h1 className="mt-5 text-3xl font-semibold tracking-[-0.04em]">LogGPT</h1>
      <div className="mt-2 text-sm text-[#777]">By Enterprise Search</div>
      <p className="mt-4 max-w-lg text-[17px] leading-7">
        Ask questions across logs, dashboards, and internal RAG sources.
      </p>

      <div className="mt-14 grid w-full max-w-[820px] gap-4 sm:grid-cols-4">
        {PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => onPrompt(prompt)}
            disabled={isSending}
            className="min-h-[92px] rounded-2xl bg-[#fafafa] p-4 text-left text-[15px] leading-6 shadow-[0_8px_30px_rgba(0,0,0,0.04)] transition hover:bg-[#f2f2f2] disabled:opacity-60"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}

function Conversation({ activeTools, messages, isSending }) {
  return (
    <div className="mx-auto max-w-[760px] space-y-5 pt-6">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      {isSending
        ? <div className="rounded-2xl bg-[#f7f7f7] px-4 py-3 text-sm text-[#777]">
            <div>The agent is thinking.</div>
            {activeTools.length ? <ToolStatus tools={activeTools} /> : null}
          </div>
        : null}
    </div>
  );
}

function Composer({
  canSend,
  error,
  input,
  isSending,
  onChange,
  onKeyDown,
  onSubmit,
  textareaRef,
}) {
  return (
    <div className="pointer-events-none absolute bottom-0 left-0 right-0 bg-white px-4 pb-5 pt-6">
      <div className="absolute inset-x-0 -top-8 h-8 bg-gradient-to-t from-white via-white/90 to-white/0" />
      <div className="mx-auto max-w-[860px]">
        {error
          ? <div className="mb-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          : null}
        <form
          onSubmit={onSubmit}
          className="pointer-events-auto rounded-[28px] border border-black/5 bg-white p-3 shadow-[0_12px_40px_rgba(0,0,0,0.10)]"
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
            placeholder="Ask anything"
            className="max-h-32 min-h-8 w-full resize-none bg-transparent px-2 text-[16px] leading-6 outline-none placeholder:text-[#9b9b9b]"
          />
          <div className="mt-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="grid h-8 w-8 place-items-center rounded-full border border-black/10 text-xl"
              >
                +
              </button>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="grid h-8 w-8 place-items-center rounded-full border border-black/10 text-[#222] transition hover:bg-[#f5f5f5]"
                aria-label="Voice input"
              >
                <span className="relative block h-4 w-3">
                  <span className="absolute left-1/2 top-0 h-2.5 w-2 -translate-x-1/2 rounded-full border border-current" />
                  <span className="absolute left-1/2 top-[8px] h-2.5 w-px -translate-x-1/2 bg-current" />
                  <span className="absolute bottom-1 left-1/2 h-1.5 w-3 -translate-x-1/2 rounded-b-full border-b border-l border-r border-current" />
                  <span className="absolute bottom-0 left-1/2 h-px w-2 -translate-x-1/2 bg-current" />
                </span>
              </button>
              <button
                type="submit"
                disabled={!canSend}
                className="grid h-8 w-8 place-items-center rounded-full bg-black text-sm font-semibold text-white transition hover:bg-[#333] disabled:bg-[#d8d8d8]"
                aria-label="Send message"
              >
                {isSending ? "..." : "↑"}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

function ToolStatus({ tools, compact = false }) {
  return (
    <output
      className={`flex flex-wrap gap-2 ${compact ? "mb-2" : "mt-3"}`}
      aria-label="Internal tools"
    >
      {tools.map((tool) => (
        <span
          key={tool.name}
          className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${
            tool.status === "running"
              ? "border-amber-200 bg-amber-50 text-amber-800"
              : "border-emerald-200 bg-emerald-50 text-emerald-800"
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              tool.status === "running"
                ? "animate-pulse bg-amber-500"
                : "bg-emerald-500"
            }`}
          />
          {formatToolName(tool.name)}
        </span>
      ))}
    </output>
  );
}

function formatToolName(name) {
  return name.replaceAll("_", " ");
}
