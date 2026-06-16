"use client";

import { useMemo, useRef, useState } from "react";
import { queryEnterpriseAgent } from "@/lib/api";
import MessageBubble from "./MessageBubble";

const PROMPTS = [
  "Find payment 5xx errors",
  "Create dashboard by service",
  "Check database timeout runbooks",
  "Show top services with errors",
];

const HISTORY = {
  Yesterday: [
    "AI Capabilities",
    "Payment timeout analysis",
    "Gateway 5xx comparison",
  ],
  "Previous 30 Days": [
    "Dashboard by endpoint",
    "RAG source validation",
    "Order failure trends",
    "OpenSearch mock logs",
    "Worker ingestion runtime",
  ],
};

function createMessageId() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export default function ChatWindow() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const textareaRef = useRef(null);

  const canSend = input.trim().length > 0 && !isSending;
  const hasConversation = messages.length > 0;
  const latestToolCalls = useMemo(() => {
    const latest = messages
      .filter((message) => message.role === "assistant" && message.data)
      .at(-1);
    return latest?.data?.tool_calls || [];
  }, [messages]);

  async function sendMessage(text) {
    const question = text.trim();

    if (!question || isSending) {
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
    setIsSending(true);

    try {
      const result = await queryEnterpriseAgent(question);
      setMessages((current) => [
        ...current,
        {
          id: createMessageId(),
          role: "assistant",
          content:
            result.answer ||
            "The agent completed the request, but did not return an answer.",
          data: result,
        },
      ]);
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : "Unable to reach the enterprise agent.";

      setError(message);
      setMessages((current) => [
        ...current,
        {
          id: createMessageId(),
          role: "assistant",
          content: `I could not complete that request. ${message}`,
          data: null,
        },
      ]);
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

  return (
    <main className="min-h-screen bg-white text-[#101010]">
      <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[280px_1fr]">
        <Sidebar onPrompt={sendMessage} isSending={isSending} />

        <section className="relative flex min-h-screen flex-col">
          <TopBar />

          <div className="flex-1 overflow-y-auto px-4 pb-44 pt-8">
            <div className="mx-auto max-w-[860px]">
              {hasConversation
                ? <Conversation messages={messages} isSending={isSending} />
                : <EmptyState onPrompt={sendMessage} isSending={isSending} />}
            </div>
          </div>

          <Composer
            canSend={canSend}
            error={error}
            input={input}
            isSending={isSending}
            latestToolCalls={latestToolCalls}
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

function Sidebar({ onPrompt, isSending }) {
  return (
    <aside className="hidden bg-[#f7f7f7] px-3 py-3 lg:flex lg:flex-col">
      <div className="flex h-10 items-center justify-between px-1">
        <button type="button" className="grid h-8 w-8 place-items-center">
          <span className="h-4 w-4 rounded-sm border border-black" />
        </button>
        <div className="flex items-center gap-3 text-xl">
          <button type="button" aria-label="Search">
            ⌕
          </button>
          <button type="button" aria-label="New chat">
            ⌑
          </button>
        </div>
      </div>

      <div className="mt-6 space-y-1">
        {[
          "Enterprise Agent",
          "Log Analyst",
          "Dashboard Builder",
          "RAG Search",
        ].map((item, index) => (
          <button
            key={item}
            type="button"
            onClick={() => onPrompt(item)}
            disabled={isSending}
            className={`flex h-10 w-full items-center gap-3 rounded-xl px-3 text-left text-[15px] transition hover:bg-[#eeeeee] disabled:opacity-60 ${
              index === 0 ? "bg-[#eeeeee]" : ""
            }`}
          >
            <span
              className={`h-6 w-6 rounded-full ${
                index === 0 ? "bg-black" : "bg-[#d8d8d8]"
              }`}
            />
            {item}
          </button>
        ))}
      </div>

      <nav className="mt-8 flex-1 overflow-y-auto px-1">
        {Object.entries(HISTORY).map(([section, items]) => (
          <div key={section} className="mb-7">
            <div className="mb-2 px-2 text-sm font-semibold">{section}</div>
            <div className="space-y-0.5">
              {items.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => onPrompt(item)}
                  disabled={isSending}
                  className="block h-9 w-full truncate rounded-xl px-2 text-left text-[15px] transition hover:bg-[#eeeeee] disabled:opacity-60"
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <button
        type="button"
        className="mb-1 flex items-center gap-3 rounded-2xl bg-[#eeeeee] p-3 text-left"
      >
        <span className="grid h-9 w-9 place-items-center rounded-full bg-white text-lg">
          ✦
        </span>
        <span>
          <span className="block text-sm font-semibold">Upgrade plan</span>
          <span className="block text-xs text-[#777]">
            More access to the best models
          </span>
        </span>
      </button>
    </aside>
  );
}

function TopBar() {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between px-5">
      <button type="button" className="text-[17px] font-medium">
        Enterprise Agent <span className="text-[#777]">⌄</span>
      </button>
      <div className="h-8 w-8 rounded-full bg-gradient-to-br from-[#e6d7c8] to-[#1f2937]" />
    </header>
  );
}

function EmptyState({ onPrompt, isSending }) {
  return (
    <div className="flex min-h-[calc(100vh-15rem)] flex-col items-center justify-center text-center">
      <div className="h-20 w-20 rounded-full bg-gradient-to-br from-[#e1e1e1] via-[#cfcfcf] to-[#222]" />
      <h1 className="mt-5 text-3xl font-semibold tracking-[-0.04em]">
        Enterprise Agent
      </h1>
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

function Conversation({ messages, isSending }) {
  return (
    <div className="mx-auto max-w-[760px] space-y-5 pt-6">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      {isSending
        ? <div className="rounded-2xl bg-[#f7f7f7] px-4 py-3 text-sm text-[#777]">
            The agent is thinking.
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
  latestToolCalls,
  onChange,
  onKeyDown,
  onSubmit,
  textareaRef,
}) {
  return (
    <div className="fixed bottom-5 left-0 right-0 px-4 lg:left-[280px]">
      <div className="mx-auto max-w-[860px]">
        {error
          ? <div className="mb-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          : null}

        <form
          onSubmit={onSubmit}
          className="rounded-[28px] border border-black/5 bg-white p-3 shadow-[0_12px_40px_rgba(0,0,0,0.10)]"
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
              {latestToolCalls.slice(0, 2).map((tool) => (
                <span
                  key={tool}
                  className="hidden rounded-full border border-black/10 px-3 py-1 text-xs text-[#777] sm:inline-flex"
                >
                  {tool}
                </span>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="grid h-8 w-8 place-items-center rounded-full border border-black/10 text-sm"
                aria-label="Voice input"
              >
                mic
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
