import { ACTION_STYLE } from "../lib/format";
import type { Action, DecisionStatus } from "../types";

export const STATUS_STYLE: Record<DecisionStatus, { label: string; className: string }> = {
  auto_approved: { label: "Auto-approved", className: "bg-slate-100 text-slate-600 ring-slate-500/20" },
  needs_officer_review: { label: "Needs officer review", className: "bg-amber-100 text-amber-900 ring-amber-600/30" },
  approved: { label: "Approved", className: "bg-emerald-100 text-emerald-800 ring-emerald-600/20" },
  overridden: { label: "Overridden", className: "bg-violet-100 text-violet-800 ring-violet-600/20" },
};

export function StatusBadge({ status }: { status: DecisionStatus }) {
  const s = STATUS_STYLE[status];
  return (
    <span
      className={`shrink-0 whitespace-nowrap rounded px-1.5 py-0.5 text-[10px] font-semibold ring-1 ring-inset ${s.className}`}
    >
      {s.label}
    </span>
  );
}

export function ActionBadge({ action }: { action: Action }) {
  return (
    <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ring-1 ring-inset ${ACTION_STYLE[action].badge}`}>
      {action}
    </span>
  );
}
