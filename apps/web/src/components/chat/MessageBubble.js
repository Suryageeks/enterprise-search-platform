import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <article
      className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser ? <Avatar label="AI" /> : null}
      <div
        className={`max-w-[min(680px,86%)] ${
          isUser
            ? "rounded-3xl bg-[#f3f3f3] px-4 py-3 text-[#1f1f1f]"
            : "px-1 py-1 text-[#1f1f1f]"
        }`}
      >
        {isUser
          ? <div className="whitespace-pre-wrap text-[14px] leading-6">
              {message.content}
            </div>
          : <MarkdownAnswer content={message.content} />}
        {!isUser ? <StructuredPreview data={message.data} /> : null}
      </div>
      {isUser ? <Avatar label="You" dark /> : null}
    </article>
  );
}

function MarkdownAnswer({ content }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => (
          <p className="mb-3 text-[14px] leading-6 last:mb-0">{children}</p>
        ),
        ul: ({ children }) => (
          <ul className="mb-3 list-disc space-y-1 pl-5 text-[14px] leading-6 last:mb-0">
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol className="mb-3 list-decimal space-y-1 pl-5 text-[14px] leading-6 last:mb-0">
            {children}
          </ol>
        ),
        li: ({ children }) => <li className="pl-1">{children}</li>,
        strong: ({ children }) => (
          <strong className="font-semibold text-[#111]">{children}</strong>
        ),
        code: ({ children }) => (
          <code className="rounded-md bg-[#f3f3f3] px-1.5 py-0.5 text-[13px]">
            {children}
          </code>
        ),
        pre: ({ children }) => (
          <pre className="mb-3 overflow-x-auto rounded-xl bg-[#f7f7f7] p-3 text-[13px] leading-5">
            {children}
          </pre>
        ),
        table: ({ children }) => (
          <div className="mb-3 overflow-x-auto">
            <table className="w-full border-collapse text-[13px]">
              {children}
            </table>
          </div>
        ),
        th: ({ children }) => (
          <th className="border border-neutral-200 bg-neutral-50 px-2 py-1 text-left font-semibold">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="border border-neutral-200 px-2 py-1">{children}</td>
        ),
      }}
    >
      {content || ""}
    </ReactMarkdown>
  );
}

function Avatar({ label, dark = false }) {
  return (
    <div
      className={`mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold ${
        dark
          ? "bg-[#f3f3f3] text-[#4b4b4b]"
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
  const hasRemediation = Boolean(data.remediation);
  const hasTools = data.tool_calls?.length > 0;
  const warnings = data.warnings || [];
  const stats = [
    logsCount ? { label: "Logs", value: logsCount } : null,
    sourcesCount ? { label: "Sources", value: sourcesCount } : null,
    aggregationsCount
      ? { label: "Aggregations", value: aggregationsCount }
      : null,
    hasDashboard ? { label: "Dashboard", value: "Ready" } : null,
  ].filter(Boolean);

  if (
    !logsCount &&
    !sourcesCount &&
    !aggregationsCount &&
    !hasDashboard &&
    !hasRemediation &&
    !warnings.length &&
    !hasTools
  ) {
    return null;
  }

  return (
    <div className="mt-4 space-y-3 border-t border-neutral-100 pt-4">
      {data.status === "partial" || data.status === "error"
        ? <div
            className={`rounded-lg px-3 py-2 text-xs ${
              data.status === "error"
                ? "bg-red-50 text-red-700"
                : "bg-amber-50 text-amber-800"
            }`}
          >
            {data.status === "error"
              ? "The investigation could not retrieve usable evidence."
              : "The answer uses partial results because one or more tools failed."}
          </div>
        : null}

      {warnings.length
        ? <ul className="space-y-1 text-xs text-amber-800">
            {[...new Set(warnings)].map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        : null}

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

      {stats.length
        ? <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((stat) => (
              <PreviewStat
                key={stat.label}
                label={stat.label}
                value={stat.value}
              />
            ))}
          </div>
        : null}

      {hasRemediation
        ? <div className="text-xs font-medium text-emerald-700">
            Evidence-validated remediation available
          </div>
        : null}

      {logsCount ? <LogsPreview logs={data.logs} /> : null}
      {sourcesCount ? <SourcesPreview sources={data.sources} /> : null}
    </div>
  );
}

function PreviewStat({ label, value }) {
  return (
    <div className="rounded-xl border border-neutral-100 bg-neutral-50 px-3 py-2">
      <div className="text-[11px] font-medium uppercase tracking-wide text-neutral-400">
        {label}
      </div>
      <div className="mt-1 text-xs font-semibold text-neutral-800">{value}</div>
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
            key={[
              log.trace_id,
              log.request_id,
              log.timestamp,
              log.service,
              index,
            ]
              .filter(Boolean)
              .join("-")}
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
            key={[source.doc_id, source.file_name, source.chunk_index, index]
              .filter((value) => value !== undefined && value !== null)
              .join("-")}
            className="rounded-full bg-white px-2.5 py-1 text-xs text-neutral-600"
          >
            {source.file_name || source.doc_id || "source"}
          </span>
        ))}
      </div>
    </div>
  );
}
