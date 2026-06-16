const DEFAULT_AGENT_API_URL = "/api/agent";

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

  return {
    answer: normalizeAnswer(payload?.answer),
    tool_calls: payload?.tool_calls || [],
    logs: payload?.logs || [],
    aggregations: payload?.aggregations || [],
    sources: payload?.sources || [],
    dashboard: payload?.dashboard || null,
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
