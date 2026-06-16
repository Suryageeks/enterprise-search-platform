const DEFAULT_BACKEND_STREAM_URL = "http://localhost:9080/api/agents/stream";

export async function POST(request) {
  const backendUrl =
    process.env.AGENT_STREAM_API_URL ||
    process.env.NEXT_PUBLIC_BACKEND_AGENT_STREAM_API_URL ||
    DEFAULT_BACKEND_STREAM_URL;

  try {
    const body = await request.text();

    const response = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body,
      cache: "no-store",
    });

    if (!response.body) {
      return Response.json(
        { detail: "Backend did not return a stream." },
        { status: 502 },
      );
    }

    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (error) {
    return Response.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : "Unable to reach the agent stream.",
      },
      { status: 502 },
    );
  }
}
