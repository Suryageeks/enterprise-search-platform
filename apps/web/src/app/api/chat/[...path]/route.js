const DEFAULT_CHAT_API_URL = "http://localhost:8091/api/chat";

export async function GET(request, context) {
  return proxyChatRequest(request, context);
}

export async function POST(request, context) {
  return proxyChatRequest(request, context);
}

export async function PATCH(request, context) {
  return proxyChatRequest(request, context);
}

export async function DELETE(request, context) {
  return proxyChatRequest(request, context);
}

async function proxyChatRequest(request, context) {
  const { path = [] } = await context.params;
  const backendBaseUrl = (
    process.env.CHAT_API_URL || DEFAULT_CHAT_API_URL
  ).replace(/\/$/, "");
  const incomingUrl = new URL(request.url);
  const backendUrl = `${backendBaseUrl}/${path.map(encodeURIComponent).join("/")}${incomingUrl.search}`;
  const hasBody = !["GET", "HEAD"].includes(request.method);

  try {
    const response = await fetch(backendUrl, {
      method: request.method,
      headers: {
        Accept: request.headers.get("accept") || "application/json",
        "Content-Type":
          request.headers.get("content-type") || "application/json",
      },
      body: hasBody ? await request.text() : undefined,
      cache: "no-store",
    });

    const contentType =
      response.headers.get("content-type") || "application/json";
    const headers = {
      "Content-Type": contentType,
      "Cache-Control": "no-cache, no-transform",
    };

    if (contentType.includes("text/event-stream")) {
      headers.Connection = "keep-alive";
      headers["X-Accel-Buffering"] = "no";
    }

    return new Response(response.body, {
      status: response.status,
      headers,
    });
  } catch (error) {
    return Response.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : "Unable to reach the chat service.",
      },
      { status: 502 },
    );
  }
}
