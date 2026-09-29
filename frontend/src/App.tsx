import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router";

import { getDecisionSummaries, getHealth, getReviewQueue } from "./api";
import DetailPanel from "./components/DetailPanel";
import PanchayatMap from "./components/PanchayatMap";
import ReviewQueue from "./components/ReviewQueue";
import { CenteredState, Spinner } from "./components/panel/Section";
import { STATUS_STYLE } from "./components/StatusBadge";
import { ACTION_STYLE, humanize, pct } from "./lib/format";
import { useAsync } from "./lib/useAsync";
import type { DecisionStatus, DecisionSummary } from "./types";

type Tab = "queue" | "all";

export default function App() {
  // Bumped after every officer review so the map, lists and open panel refetch.
  const [version, setVersion] = useState(0);
  const refresh = () => setVersion((v) => v + 1);

  const summaries = useAsync((signal) => getDecisionSummaries(signal), [version], { keepPreviousData: true });
  const queue = useAsync((signal) => getReviewQueue(signal), [version], { keepPreviousData: true });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("queue");

  const selected = useMemo(
    () => (summaries.status === "ok" ? summaries.data.find((s) => s.panchayat.id === selectedId) : undefined),
    [summaries, selectedId],
  );
  useEffect(() => {
    document.title = "Monsoon Decision Twin · Officer Dashboard";
  }, []);

  const pendingCount = queue.status === "ok" ? queue.data.filter((i) => i.status === "needs_officer_review").length : 0;

  const refreshError =
    (summaries.status === "ok" && summaries.refreshError) || (queue.status === "ok" && queue.refreshError) || null;
  const retryAll = () => {
    summaries.reload();
    queue.reload();
  };

  return (
    <div className="flex h-screen flex-col bg-slate-100 text-slate-900">
      <Header />
      {refreshError && (
        <div role="alert" className="flex items-center gap-3 bg-amber-100 px-4 py-1.5 text-xs text-amber-900">
          <span>Couldn’t refresh: {refreshError.message} Showing the last loaded data.</span>
          <button onClick={retryAll} className="ml-auto font-semibold underline">
            Retry
          </button>
        </div>
      )}
      <main className="flex min-h-0 flex-1 flex-col md:flex-row">
        <div className="relative min-h-[50vh] flex-1">
          {summaries.status === "loading" ? (
            <Spinner label="Loading panchayats…" />
          ) : summaries.status === "error" ? (
            <CenteredState
              tone="error"
              title="Couldn’t load the map data"
              text={summaries.error.message}
              onRetry={summaries.reload}
            />
          ) : summaries.data.length === 0 ? (
            <CenteredState
              title="No panchayats yet"
              text="The database has no panchayats. The backend seeds sample data on first start; check the backend logs."
              onRetry={summaries.reload}
            />
          ) : (
            <PanchayatMap summaries={summaries.data} selectedId={selectedId} onSelect={setSelectedId} />
          )}
        </div>

        <aside className="flex max-h-[60vh] w-full flex-col border-t border-slate-200 bg-white md:max-h-none md:w-[30rem] md:border-l md:border-t-0">
          {selected ? (
            <DetailPanel
              key={selected.panchayat.id}
              summary={selected}
              version={version}
              onClose={() => setSelectedId(null)}
              onOpenQueue={() => {
                setSelectedId(null);
                setTab("queue");
              }}
            />
          ) : (
            <div className="flex h-full min-h-0 flex-col">
              <div className="flex gap-1 border-b border-slate-200 px-3 pt-3" role="tablist">
                <TabButton active={tab === "queue"} onClick={() => setTab("queue")}>
                  Review queue
                  {pendingCount > 0 && (
                    <span className="ml-1.5 rounded-full bg-amber-500 px-1.5 text-[10px] font-bold text-white">
                      {pendingCount}
                    </span>
                  )}
                </TabButton>
                <TabButton active={tab === "all"} onClick={() => setTab("all")}>
                  All panchayats
                </TabButton>
              </div>
              {tab === "queue" ? (
                queue.status === "loading" ? (
                  <Spinner label="Loading review queue…" />
                ) : queue.status === "error" ? (
                  <CenteredState
                    tone="error"
                    title="Couldn’t load the review queue"
                    text={queue.error.message}
                    onRetry={queue.reload}
                  />
                ) : (
                  <ReviewQueue items={queue.data} onOpen={setSelectedId} onChanged={refresh} />
                )
              ) : summaries.status === "loading" ? (
                <Spinner label="Loading panchayats…" />
              ) : summaries.status === "error" ? (
                <CenteredState
                  tone="error"
                  title="Couldn’t load panchayats"
                  text={summaries.error.message}
                  onRetry={summaries.reload}
                />
              ) : summaries.data.length === 0 ? (
                <CenteredState title="No panchayats yet" />
              ) : (
                <Overview summaries={summaries.data} onSelect={setSelectedId} />
              )}
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}

const HEALTH_POLL_MS = 30_000;

function Header() {
  const health = useAsync((signal) => getHealth(signal), [], { keepPreviousData: true });
  const { reload } = health;
  // Re-check periodically so the indicator recovers when the backend comes back.
  useEffect(() => {
    const id = window.setInterval(reload, HEALTH_POLL_MS);
    return () => window.clearInterval(id);
  }, [reload]);
  const status =
    health.status === "ok" && !health.refreshError
      ? { dot: "bg-emerald-500", text: `Backend ok · ${health.data.database.dialect}` }
      : health.status !== "loading"
        ? { dot: "bg-red-500", text: "Backend unreachable" }
        : { dot: "bg-amber-400 animate-pulse", text: "Connecting…" };

  return (
    <header className="flex items-center gap-4 border-b border-slate-800 bg-slate-900 px-4 py-2.5 text-white">
      <div>
        <h1 className="text-base font-semibold leading-tight">Monsoon Decision Twin</h1>
        <p className="text-[11px] text-slate-400">Officer dashboard · Maharashtra · next 4 weeks</p>
      </div>
      <Link to="/admin/feedback" className="ml-auto text-xs text-slate-300 hover:text-white">
        Farmer feedback
      </Link>
      <div className="flex items-center gap-2 text-xs text-slate-300">
        <span className={`h-2 w-2 rounded-full ${status.dot}`} />
        {status.text}
      </div>
    </header>
  );
}

/** Shown when no marker is selected: a compact, clickable list of all panchayats. */
function Overview({ summaries, onSelect }: { summaries: DecisionSummary[]; onSelect: (id: string) => void }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <p className="px-5 pb-2 pt-3 text-xs text-slate-500">
        Select a marker or a row to see forecast, scenarios and decision.
      </p>
      <div className="flex-1 overflow-y-auto px-2 pb-3">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-white">
            <tr className="text-left text-[11px] text-slate-500">
              <th className="px-3 py-1.5 font-medium">Panchayat</th>
              <th className="px-1 py-1.5 font-medium">Crop</th>
              <th className="px-1 py-1.5 font-medium">Action</th>
              <th className="px-1 py-1.5 text-right font-medium" title="Decision confidence">
                Conf.
              </th>
              <th className="px-3 py-1.5 text-right font-medium" title="Crop suitability (0-100)">
                Suit.
              </th>
            </tr>
          </thead>
          <tbody>
            {summaries.map((s) => (
              <tr
                key={s.panchayat.id}
                onClick={() => onSelect(s.panchayat.id)}
                className="cursor-pointer border-t border-slate-100 hover:bg-slate-50"
              >
                <td className="px-3 py-1.5">
                  <div className="font-medium text-slate-800">{s.panchayat.name}</div>
                  <div className="text-[10px] text-slate-400">{s.panchayat.block_name}</div>
                </td>
                <td className="px-1 py-1.5 text-slate-600">{humanize(s.crop)}</td>
                <td className="px-1 py-1.5">
                  {s.action ? (
                    <span className="flex items-center gap-1">
                      <span
                        className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ring-1 ring-inset ${ACTION_STYLE[s.action].badge}`}
                      >
                        {s.action}
                      </span>
                      {s.status && s.status !== "auto_approved" && (
                        <span className={STATUS_ICON[s.status].className} title={STATUS_STYLE[s.status].label}>
                          {STATUS_ICON[s.status].icon}
                        </span>
                      )}
                    </span>
                  ) : (
                    <span className="text-[10px] text-slate-400">not modelled</span>
                  )}
                </td>
                <td className="px-1 py-1.5 text-right tabular-nums text-slate-600">
                  {s.confidence != null ? pct(s.confidence) : "—"}
                </td>
                <td className="px-3 py-1.5 text-right tabular-nums text-slate-600">{s.suitability_score ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const STATUS_ICON: Record<Exclude<DecisionStatus, "auto_approved">, { icon: string; className: string }> = {
  needs_officer_review: { icon: "⚠", className: "text-amber-600" },
  approved: { icon: "✓", className: "text-emerald-600" },
  overridden: { icon: "✎", className: "text-violet-600" },
};

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`-mb-px flex items-center rounded-t-md border px-3 py-1.5 text-xs font-semibold ${
        active
          ? "border-slate-200 border-b-white bg-white text-slate-900"
          : "border-transparent text-slate-500 hover:text-slate-700"
      }`}
    >
      {children}
    </button>
  );
}
