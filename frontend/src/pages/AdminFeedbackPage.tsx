import { useEffect, useState } from "react";
import { Link } from "react-router";

import { getFeedback, getPanchayats } from "../api";
import { ErrorNote, Spinner } from "../components/panel/Section";
import { ActionBadge, StatusBadge } from "../components/StatusBadge";
import { humanize, pct } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import type { FarmerAction, FeedbackEntry } from "../types";

const ACTION_LABEL: Record<FarmerAction, string> = {
  sowed: "Sowed",
  waited: "Waited",
  sprayed: "Sprayed",
  nothing: "Nothing yet",
};

const LIMITS = [50, 100, 200, 500];

const timeFormatter = new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

export default function AdminFeedbackPage() {
  const [panchayatId, setPanchayatId] = useState("");
  const [limit, setLimit] = useState(50);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    document.title = "Farmer feedback · Monsoon Decision Twin";
  }, []);

  const panchayats = useAsync((signal) => getPanchayats(signal), []);
  const feedback = useAsync(
    (signal) => getFeedback({ limit, panchayatId: panchayatId || undefined }, signal),
    [limit, panchayatId, version],
    { keepPreviousData: true },
  );

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <header className="flex items-center gap-4 border-b border-slate-800 bg-slate-900 px-4 py-2.5 text-white">
        <div>
          <h1 className="text-base font-semibold leading-tight">Farmer feedback</h1>
          <p className="text-[11px] text-slate-400">Monsoon Decision Twin · admin</p>
        </div>
        <Link to="/" className="ml-auto text-xs text-slate-300 hover:text-white">
          ← Officer dashboard
        </Link>
      </header>

      <main className="mx-auto max-w-7xl space-y-4 p-4">
        <p className="rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-900">
          Reported outcomes are stored for <b>future periodic recalibration</b> of the forecast and decision
          coefficients. They are not used by any model yet.
        </p>

        <div className="flex flex-wrap items-end gap-3">
          <label className="text-xs text-slate-600">
            <span className="mb-1 block">Panchayat</span>
            <select
              value={panchayatId}
              onChange={(e) => setPanchayatId(e.target.value)}
              className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm"
            >
              <option value="">All panchayats</option>
              {panchayats.status === "ok" &&
                panchayats.data.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.block_name}) · {p.id}
                  </option>
                ))}
            </select>
          </label>
          <label className="text-xs text-slate-600">
            <span className="mb-1 block">Show</span>
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm"
            >
              {LIMITS.map((n) => (
                <option key={n} value={n}>
                  Latest {n}
                </option>
              ))}
            </select>
          </label>
          <button
            onClick={() => setVersion((v) => v + 1)}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Refresh
          </button>
        </div>

        {feedback.status === "ok" && feedback.refreshError && (
          <ErrorNote
            message={`Couldn’t refresh: ${feedback.refreshError.message} Showing the last loaded entries.`}
            onRetry={feedback.reload}
          />
        )}
        {feedback.status === "loading" ? (
          <Spinner label="Loading feedback…" />
        ) : feedback.status === "error" ? (
          <ErrorNote message={feedback.error.message} onRetry={feedback.reload} />
        ) : feedback.data.length === 0 ? (
          panchayatId ? (
            <p className="rounded-lg bg-white p-6 text-sm text-slate-600 shadow-sm ring-1 ring-slate-900/5">
              No feedback from this panchayat yet.
            </p>
          ) : (
            <EmptyState />
          )
        ) : (
          <>
            <Summary entries={feedback.data} />
            <FeedbackTable entries={feedback.data} />
          </>
        )}
      </main>
    </div>
  );
}

function Summary({ entries }: { entries: FeedbackEntry[] }) {
  const rain = entries.filter((e) => e.rain_occurred).length;
  const withAdvice = entries.filter((e) => e.followed_advice !== null);
  const followed = withAdvice.filter((e) => e.followed_advice).length;

  return (
    <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <Tile label="Entries shown" value={String(entries.length)} />
      <Tile label="Reported rain" value={pct(rain / entries.length)} sub={`${rain} of ${entries.length}`} />
      <Tile
        label="Followed the advice"
        value={withAdvice.length ? pct(followed / withAdvice.length) : "—"}
        sub={withAdvice.length ? `${followed} of ${withAdvice.length} with advice` : "no advised entries"}
      />
    </dl>
  );
}

function Tile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg bg-white px-4 py-3 shadow-sm ring-1 ring-slate-900/5">
      <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 text-2xl font-semibold tabular-nums">{value}</dd>
      {sub && <dd className="text-xs text-slate-500">{sub}</dd>}
    </div>
  );
}

function FeedbackTable({ entries }: { entries: FeedbackEntry[] }) {
  return (
    <div className="overflow-x-auto rounded-lg bg-white shadow-sm ring-1 ring-slate-900/5">
      <table className="w-full min-w-[56rem] text-sm">
        <thead className="border-b border-slate-200 bg-slate-50 text-left text-[11px] uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-3 py-2 font-medium">Submitted</th>
            <th className="px-3 py-2 font-medium">Panchayat</th>
            <th className="px-3 py-2 font-medium">Crop</th>
            <th className="px-3 py-2 font-medium">Rain?</th>
            <th className="px-3 py-2 font-medium">Farmer did</th>
            <th className="px-3 py-2 font-medium">Advice shown</th>
            <th className="px-3 py-2 text-center font-medium">Followed?</th>
            <th className="px-3 py-2 font-medium">Note</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {entries.map((e) => (
            <tr key={e.id} className="align-top">
              <td className="whitespace-nowrap px-3 py-2 tabular-nums text-slate-600">
                {timeFormatter.format(new Date(e.submitted_at))}
              </td>
              <td className="px-3 py-2">
                <div className="font-medium">{e.panchayat_name}</div>
                <div className="text-[11px] text-slate-400">
                  {e.block_name} · {e.panchayat_id}
                </div>
              </td>
              <td className="px-3 py-2 text-slate-600">{humanize(e.crop)}</td>
              <td className="px-3 py-2">
                <span
                  className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${
                    e.rain_occurred ? "bg-blue-100 text-blue-800" : "bg-orange-100 text-orange-800"
                  }`}
                >
                  {e.rain_occurred ? "Yes" : "No"}
                </span>
              </td>
              <td className="px-3 py-2 text-slate-700">{ACTION_LABEL[e.action_taken]}</td>
              <td className="px-3 py-2">
                {e.advised_action ? (
                  <div className="flex flex-col items-start gap-1">
                    <ActionBadge action={e.advised_action} />
                    {e.advice_status && e.advice_status !== "auto_approved" && <StatusBadge status={e.advice_status} />}
                    {e.model_confidence != null && (
                      <span className="text-[10px] text-slate-400">model conf. {pct(e.model_confidence)}</span>
                    )}
                  </div>
                ) : (
                  <span className="text-[11px] text-slate-400">no advice model</span>
                )}
              </td>
              <td className="px-3 py-2 text-center">
                {e.followed_advice === null ? (
                  <span className="text-slate-300">—</span>
                ) : e.followed_advice ? (
                  <span className="font-semibold text-emerald-600" title="Followed the advice">
                    ✓
                  </span>
                ) : (
                  <span className="font-semibold text-red-600" title="Did something else">
                    ✗
                  </span>
                )}
              </td>
              <td className="max-w-xs px-3 py-2 text-slate-600">
                {e.note ?? <span className="text-slate-300">—</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-lg bg-white p-6 text-sm text-slate-600 shadow-sm ring-1 ring-slate-900/5">
      <p className="font-medium text-slate-800">No feedback yet.</p>
      <p className="mt-1">Farmers' reports appear here once submitted to the API, for example:</p>
      <pre className="mt-3 overflow-x-auto rounded bg-slate-900 p-3 text-xs text-slate-100">
        {`POST /feedback
{ "panchayat_id": "GP014", "rain_occurred": true, "action_taken": "sowed", "note": "optional" }`}
      </pre>
    </div>
  );
}
