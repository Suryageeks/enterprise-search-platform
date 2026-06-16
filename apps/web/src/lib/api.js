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
    answer: payload?.answer || "",
    tool_calls: payload?.tool_calls || [],
    logs: payload?.logs || [],
    aggregations: payload?.aggregations || [],
    sources: payload?.sources || [],
    dashboard: payload?.dashboard || null,
  };
}
