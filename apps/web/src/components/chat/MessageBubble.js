export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <article
      className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser ? <Avatar label="AI" /> : null}
      <div
        className={`max-w-[min(720px,85%)] rounded-3xl px-5 py-4 shadow-sm ${
          isUser
            ? "bg-neutral-950 text-white"
            : "border border-neutral-200 bg-white text-neutral-900"
        }`}
      >
        <div className="whitespace-pre-wrap text-[15px] leading-7">
          {message.content}
        </div>
        {!isUser ? <StructuredPreview data={message.data} /> : null}
      </div>
      {isUser ? <Avatar label="You" dark /> : null}
    </article>
  );
}

function Avatar({ label, dark = false }) {
  return (
    <div
      className={`mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold ${
        dark
          ? "bg-neutral-950 text-white"
          : "border border-neutral-200 bg-white text-neutral-700"
      }`}
    >
      {label}
    </div>
  );
}

function StructuredPreview({ data }) {
  if (!data) {
    return null;
  }

  const logsCount = data.logs?.length || 0;
  const sourcesCount = data.sources?.length || 0;
  const aggregationsCount = data.aggregations?.length || 0;
  const hasDashboard = Boolean(data.dashboard);
  const hasTools = data.tool_calls?.length > 0;

  if (
    !logsCount &&
    !sourcesCount &&
    !aggregationsCount &&
    !hasDashboard &&
    !hasTools
  ) {
    return null;
  }

  return (
    <div className="mt-4 space-y-3 border-t border-neutral-100 pt-4">
      {hasTools
        ? <div className="flex flex-wrap gap-2">
            {[...new Set(data.tool_calls)].map((tool) => (
              <span
                key={tool}
                className="rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-600"
              >
                {tool}
              </span>
            ))}
          </div>
        : null}

      <div className="grid gap-2 sm:grid-cols-4">
        <PreviewStat label="Logs" value={logsCount} />
        <PreviewStat label="Sources" value={sourcesCount} />
        <PreviewStat label="Aggregations" value={aggregationsCount} />
        <PreviewStat
          label="Dashboard"
          value={hasDashboard ? "Ready" : "None"}
        />
      </div>

      {logsCount ? <LogsPreview logs={data.logs} /> : null}
      {sourcesCount ? <SourcesPreview sources={data.sources} /> : null}
    </div>
  );
}

function PreviewStat({ label, value }) {
  return (
    <div className="rounded-2xl border border-neutral-100 bg-neutral-50 px-3 py-2">
      <div className="text-[11px] font-medium uppercase tracking-wide text-neutral-400">
        {label}
      </div>
      <div className="mt-1 text-sm font-semibold text-neutral-800">{value}</div>
    </div>
  );
}

function LogsPreview({ logs }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-neutral-100">
      <div className="bg-neutral-50 px-3 py-2 text-xs font-semibold text-neutral-500">
        Recent evidence
      </div>
      <div className="divide-y divide-neutral-100">
        {logs.slice(0, 3).map((log, index) => (
          <div
            key={`${log.trace_id || log.request_id || index}`}
            className="grid gap-1 px-3 py-2 text-xs text-neutral-600 sm:grid-cols-[120px_1fr]"
          >
            <span className="font-medium text-neutral-800">
              {log.service || "unknown"}
            </span>
            <span className="truncate">
              {log.message || log.endpoint || "No message"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SourcesPreview({ sources }) {
  return (
    <div className="rounded-2xl border border-neutral-100 bg-neutral-50 px-3 py-2">
      <div className="text-xs font-semibold text-neutral-500">Sources</div>
      <div className="mt-2 flex flex-wrap gap-2">
        {sources.slice(0, 4).map((source, index) => (
          <span
            key={`${source.doc_id || source.file_name || index}`}
            className="rounded-full bg-white px-2.5 py-1 text-xs text-neutral-600"
          >
            {source.file_name || source.doc_id || "source"}
          </span>
        ))}
      </div>
    </div>
  );
}
