const DEFAULT_BACKEND_AGENT_URL = "http://localhost:9080/api/agents/query";

export async function POST(request) {
  const backendUrl =
    process.env.AGENT_API_URL ||
    process.env.NEXT_PUBLIC_BACKEND_AGENT_API_URL ||
    DEFAULT_BACKEND_AGENT_URL;

  const body = await request.json();

  try {
    const response = await postJson(backendUrl, body);
    const payload = await readJson(response);

    if (response.status !== 404) {
      return Response.json(normalizeAgentPayload(payload), {
        status: response.status,
      });
    }

    const fallbackUrl = backendUrl.replace(
      "/api/agents/query",
      "/api/analysis/query",
    );

    if (fallbackUrl === backendUrl) {
      return Response.json(payload || { detail: "Agent route not found." }, {
        status: response.status,
      });
    }

    const fallbackResponse = await postJson(fallbackUrl, {
      message: body.question,
      top_k: body.top_k || 5,
    });
    const fallbackPayload = await readJson(fallbackResponse);

    return Response.json(normalizeAnalysisPayload(fallbackPayload), {
      status: fallbackResponse.status,
    });
  } catch (error) {
    return Response.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : "Unable to reach the agent service.",
      },
      { status: 502 },
    );
  }
}

async function postJson(url, body) {
  return fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });
}

async function readJson(response) {
  try {
    return await response.json();
  } catch (error) {
    return {
      detail:
        error instanceof Error
          ? error.message
          : "Backend returned invalid JSON.",
    };
  }
}

function normalizeAgentPayload(payload) {
  return {
    answer: normalizeAnswer(payload?.answer || payload?.detail || ""),
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

function normalizeAnalysisPayload(payload) {
  return {
    answer: normalizeAnswer(payload?.answer || payload?.detail || ""),
    status: "success",
    tool_calls: payload?.intent ? [`router:${payload.intent}`] : [],
    tool_results: [],
    warnings: [],
    logs: payload?.logs || payload?.evidence || [],
    aggregations: payload?.aggregations || [],
    sources: payload?.sources || [],
    dashboard: payload?.dashboard || null,
    remediation: null,
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
