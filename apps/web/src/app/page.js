import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#f7f7f8_0,#ffffff_42%,#f5f5f4_100%)] px-5 py-8 text-neutral-950">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-6xl flex-col">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-neutral-200 bg-white shadow-sm">
              <span className="h-2.5 w-2.5 rounded-full bg-neutral-950" />
            </div>
            <span className="text-sm font-medium tracking-tight">
              Enterprise Search
            </span>
          </div>
          <Link
            href="/chat"
            className="rounded-full border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-800 shadow-sm transition hover:border-neutral-300 hover:bg-neutral-50"
          >
            Open chat
          </Link>
        </header>

        <section className="flex flex-1 items-center py-16">
          <div className="max-w-3xl">
            <div className="mb-5 inline-flex rounded-full border border-neutral-200 bg-white px-3 py-1 text-xs font-medium text-neutral-600 shadow-sm">
              RAG, logs, dashboards, and agent tools in one workspace
            </div>
            <h1 className="max-w-3xl text-5xl font-semibold leading-[1.04] tracking-[-0.03em] text-neutral-950 sm:text-7xl">
              Ask your systems what happened.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-neutral-600">
              A focused chat interface for querying logs, runbooks, RAG sources,
              and generated dashboards from the enterprise agent.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/chat"
                className="rounded-full bg-neutral-950 px-5 py-3 text-sm font-medium text-white shadow-lg shadow-neutral-950/10 transition hover:bg-neutral-800"
              >
                Start asking
              </Link>
              <span className="rounded-full border border-neutral-200 bg-white px-5 py-3 text-sm font-medium text-neutral-600 shadow-sm">
                Backend: /api/agents/query
              </span>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
