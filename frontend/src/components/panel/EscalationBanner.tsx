import type { Escalation } from "../../types";
import { ActionBadge, StatusBadge } from "../StatusBadge";

/** Officer-review state of the decision, shown above the recommendation. */
interface Props {
  escalation: Escalation;
  /** False for what-if crops: only primary-crop decisions are in the review queue. */
  inQueue: boolean;
  onOpenQueue: () => void;
}

export default function EscalationBanner({ escalation: esc, inQueue, onOpenQueue }: Props) {
  if (esc.status === "auto_approved") return null;

  const tone =
    esc.status === "needs_officer_review"
      ? "border-amber-300 bg-amber-50"
      : esc.status === "overridden"
        ? "border-violet-200 bg-violet-50"
        : "border-emerald-200 bg-emerald-50";

  return (
    <div className={`mx-5 mt-4 rounded-lg border px-3 py-2.5 text-xs ${tone}`}>
      <div className="flex items-center justify-between gap-2">
        <StatusBadge status={esc.status} />
        {esc.status === "overridden" && (
          <span className="flex items-center gap-1 text-slate-600">
            Final action: <ActionBadge action={esc.final_action} />
          </span>
        )}
      </div>
      <ul className="mt-2 space-y-0.5 text-slate-700">
        {esc.reasons.map((r) => (
          <li key={r.code} className="flex gap-1.5">
            <span className="text-amber-600" aria-hidden>
              ⚠
            </span>
            {r.message}
          </li>
        ))}
      </ul>
      {esc.review?.note && (
        <p className="mt-2 text-slate-600">
          <span className="font-medium">Officer note:</span> {esc.review.note}
        </p>
      )}
      {esc.status === "needs_officer_review" &&
        (inQueue ? (
          <button onClick={onOpenQueue} className="mt-2 font-medium text-sky-700 hover:underline">
            Review in queue →
          </button>
        ) : (
          <p className="mt-2 text-slate-500">
            The review queue lists primary-crop decisions only; this crop is a what-if.
          </p>
        ))}
    </div>
  );
}
