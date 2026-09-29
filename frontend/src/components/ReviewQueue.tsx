import { useState } from "react";

import { approveReview, overrideReview } from "../api";
import { ACTION_STYLE, humanize, inr, pct } from "../lib/format";
import type { Action, ReviewItem } from "../types";
import { ActionBadge, StatusBadge } from "./StatusBadge";

interface Props {
  items: ReviewItem[];
  onOpen: (panchayatId: string) => void;
  onChanged: () => void;
}

export default function ReviewQueue({ items, onOpen, onChanged }: Props) {
  const pending = items.filter((i) => i.status === "needs_officer_review");
  const reviewed = items.filter((i) => i.status !== "needs_officer_review");

  return (
    <div className="flex-1 overflow-y-auto px-3 pb-4">
      {items.length === 0 ? (
        <p className="mx-2 my-3 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
          No decisions need officer review today. Everything was auto-approved.
        </p>
      ) : pending.length === 0 ? (
        <p className="mx-2 my-3 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          All flagged decisions for today have been reviewed.
        </p>
      ) : (
        <ul className="space-y-2">
          {pending.map((item) => (
            <QueueItem key={item.id} item={item} onOpen={onOpen} onChanged={onChanged} />
          ))}
        </ul>
      )}

      {reviewed.length > 0 && (
        <>
          <h3 className="mx-2 mb-2 mt-5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Reviewed today
          </h3>
          <ul className="space-y-2">
            {reviewed.map((item) => (
              <QueueItem key={item.id} item={item} onOpen={onOpen} onChanged={onChanged} />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function QueueItem({
  item,
  onOpen,
  onChanged,
}: {
  item: ReviewItem;
  onOpen: (id: string) => void;
  onChanged: () => void;
}) {
  const isPending = item.status === "needs_officer_review";
  const [mode, setMode] = useState<"idle" | "override">("idle");
  const [editing, setEditing] = useState(isPending);
  const [overrideAction, setOverrideAction] = useState<Action | "">("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      setMode("idle");
      setNote("");
      setOverrideAction("");
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const alternatives = (Object.keys(ACTION_STYLE) as Action[]).filter((a) => a !== item.recommended_action);
  const canOverride = overrideAction !== "" && note.trim().length >= 3;

  return (
    <li
      className={`rounded-lg border p-3 ${isPending ? "border-amber-300 bg-amber-50/40" : "border-slate-200 bg-white"}`}
    >
      <div className="flex items-start justify-between gap-2">
        <button onClick={() => onOpen(item.panchayat.id)} className="text-left" title="Open full detail">
          <div className="text-sm font-semibold text-slate-900 hover:underline">{item.panchayat.name}</div>
          <div className="text-[11px] text-slate-500">
            {item.panchayat.block_name} · {humanize(item.crop)} · {item.panchayat.id}
          </div>
        </button>
        <StatusBadge status={item.status} />
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-600">
        <span className="flex items-center gap-1">
          Model: <ActionBadge action={item.recommended_action} />
        </span>
        {item.status === "overridden" && (
          <span className="flex items-center gap-1">
            → Officer: <ActionBadge action={item.final_action} />
          </span>
        )}
        <span className="tabular-nums">conf. {pct(item.confidence)}</span>
        <span className="tabular-nums">E[loss] {inr(item.expected_loss_inr_per_ha)}/ha</span>
      </div>

      <ul className="mt-2 space-y-0.5">
        {item.reasons.map((r) => (
          <li key={r.code} className="flex gap-1.5 text-[11px] text-amber-900">
            <span aria-hidden>⚠</span>
            {r.message}
          </li>
        ))}
      </ul>

      {item.review?.note && (
        <p className="mt-2 rounded bg-slate-50 px-2 py-1 text-[11px] text-slate-600">
          <span className="font-medium">Officer note:</span> {item.review.note}
        </p>
      )}

      {!editing ? (
        <button onClick={() => setEditing(true)} className="mt-2 text-[11px] font-medium text-sky-700 hover:underline">
          Change review
        </button>
      ) : mode === "idle" ? (
        <div className="mt-3 flex gap-2">
          <button
            disabled={busy}
            onClick={() => run(() => approveReview(item.id))}
            className="flex-1 rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
          >
            Approve {item.recommended_action}
          </button>
          <button
            disabled={busy}
            onClick={() => setMode("override")}
            className="flex-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Override…
          </button>
          {!isPending && (
            <button onClick={() => setEditing(false)} className="px-1 text-xs text-slate-500 hover:text-slate-700">
              Cancel
            </button>
          )}
        </div>
      ) : (
        <form
          className="mt-3 space-y-2 rounded-md border border-slate-200 bg-white p-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (canOverride) run(() => overrideReview(item.id, overrideAction as Action, note.trim()));
          }}
        >
          <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="Replacement action">
            {alternatives.map((a) => (
              <button
                type="button"
                key={a}
                role="radio"
                aria-checked={overrideAction === a}
                onClick={() => setOverrideAction(a)}
                className={`rounded px-2 py-1 text-[11px] font-semibold ring-1 ring-inset ${
                  overrideAction === a ? ACTION_STYLE[a].badge + " ring-2" : "bg-white text-slate-600 ring-slate-300"
                }`}
              >
                {a}
              </button>
            ))}
          </div>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Reason for override (required)"
            rows={2}
            maxLength={500}
            className="w-full resize-none rounded border border-slate-300 px-2 py-1 text-xs focus:border-sky-500 focus:outline-none"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={!canOverride || busy}
              className="flex-1 rounded-md bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-700 disabled:opacity-40"
            >
              Confirm override
            </button>
            <button
              type="button"
              onClick={() => setMode("idle")}
              className="px-2 text-xs text-slate-500 hover:text-slate-700"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {error && <p className="mt-2 text-[11px] text-red-700">{error}</p>}
    </li>
  );
}
