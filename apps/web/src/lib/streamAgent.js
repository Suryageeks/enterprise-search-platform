export async function streamEnterpriseAgent(question, handlers = {}) {
  const response = await fetch("/api/agent/stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  if (!response.ok || !response.body) {
    let detail = "Unable to start agent stream.";

    try {
      const payload = await response.json();
      detail = payload?.detail || detail;
    } catch {
      // Keep the default error.
    }

    throw new Error(detail);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const rawEvents = buffer.split("\n\n");
    buffer = rawEvents.pop() || "";

    for (const rawEvent of rawEvents) {
      const parsed = parseSseEvent(rawEvent);

      if (!parsed) {
        continue;
      }

      if (parsed.event === "token") {
        handlers.onToken?.(parsed.data.text || "");
      }

      if (parsed.event === "tool_start") {
        handlers.onToolStart?.(parsed.data.tool || "unknown_tool");
      }

      if (parsed.event === "tool_end") {
        handlers.onToolEnd?.(
          parsed.data.tool || "unknown_tool",
          parsed.data.result,
        );
      }

      if (parsed.event === "done") {
        handlers.onDone?.(parsed.data);
      }
    }
  }
}

function parseSseEvent(rawEvent) {
  const lines = rawEvent.split("\n");
  const eventLine = lines.find((line) => line.startsWith("event: "));
  const dataLines = lines
    .filter((line) => line.startsWith("data: "))
    .map((line) => line.replace("data: ", ""));

  if (!eventLine || dataLines.length === 0) {
    return null;
  }

  return {
    event: eventLine.replace("event: ", ""),
    data: JSON.parse(dataLines.join("\n")),
  };
}
