const DEFAULT_AGENT_API_URL = "/api/agent";
const CHAT_API_URL = "/api/chat";

export async function listChatSessions() {
  return requestJson(`${CHAT_API_URL}/sessions?limit=100`);
}

export async function createChatSession(title = null) {
  return requestJson(`${CHAT_API_URL}/sessions`, {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

export async function renameChatSession(sessionId, title) {
  return requestJson(`${CHAT_API_URL}/sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
}

export async function deleteChatSession(sessionId) {
  await requestJson(`${CHAT_API_URL}/sessions/${sessionId}`, {
    method: "DELETE",
  });
}

export async function listChatMessages(sessionId) {
  const messages = await requestJson(
    `${CHAT_API_URL}/sessions/${sessionId}/messages?limit=100`,
  );

  return messages
    .filter(
      (message) => message.role === "user" || message.role === "assistant",
    )
    .map((message) => ({
      id: message.id,
      role: message.role,
      content: message.content,
      data: message.role === "assistant" ? message.metadata || {} : null,
      createdAt: message.created_at,
    }));
}

export async function queryEnterpriseAgent(question) {
  const endpoint =
    process.env.NEXT_PUBLIC_AGENT_API_URL || DEFAULT_AGENT_API_URL;

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  let payload = null;

  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail =
      payload?.detail || payload?.message || "The agent request failed.";
    throw new Error(detail);
  }

  return normalizeAgentResult(payload);
}

export function normalizeAgentResult(payload = {}) {
  return {
    answer: normalizeAnswer(payload?.answer),
    status: payload?.status || "success",
    tool_calls: payload?.tool_calls || [],
    tool_results: payload?.tool_results || [],
    warnings: payload?.warnings || [],
    logs: payload?.logs || [],
    aggregations: payload?.aggregations || [],
    sources: payload?.sources || [],
    dashboard: payload?.dashboard || null,
    remediation: payload?.remediation || null,
  };
}

function normalizeAnswer(answer) {
  if (!answer) {
    return "";
  }

  if (Array.isArray(answer)) {
    return answer.map(extractContentPart).filter(Boolean).join("\n\n");
  }

  if (typeof answer !== "string") {
    return String(answer);
  }

  return answer;
}

function extractContentPart(part) {
  if (typeof part === "string") {
    return part;
  }

  if (part?.type === "text" && typeof part.text === "string") {
    return part.text;
  }

  if (typeof part?.content === "string") {
    return part.content;
  }

  return "";
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (response.status === 204) {
    return null;
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw new Error(
      payload?.detail || payload?.message || "The chat request failed.",
    );
  }

  return payload;
}
