import type { ReactNode } from "react";

export default function Section({ title, aside, children }: { title: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <section className="border-t border-slate-200 px-5 py-4">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{title}</h3>
        {aside && <div className="text-[11px] text-slate-400">{aside}</div>}
      </div>
      {children}
    </section>
  );
}

export function Skeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="animate-pulse space-y-2">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="h-4 rounded bg-slate-100" />
      ))}
    </div>
  );
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="flex items-start justify-between gap-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700"
    >
      <span>{message}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="shrink-0 rounded border border-red-300 bg-white px-2 py-0.5 text-xs font-medium text-red-700 hover:bg-red-100"
        >
          Try again
        </button>
      )}
    </div>
  );
}

/** Centered message for an empty or failed area (map, lists). */
export function CenteredState({
  title,
  text,
  onRetry,
  tone = "neutral",
}: {
  title: string;
  text?: string;
  onRetry?: () => void;
  tone?: "neutral" | "error";
}) {
  return (
    <div className="flex h-full min-h-40 flex-col items-center justify-center gap-2 p-6 text-center">
      <p className={`text-sm font-medium ${tone === "error" ? "text-red-700" : "text-slate-700"}`}>{title}</p>
      {text && <p className="max-w-sm text-xs text-slate-500">{text}</p>}
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
        >
          Try again
        </button>
      )}
    </div>
  );
}

export function Spinner({ label }: { label: string }) {
  return (
    <div className="flex h-full min-h-40 items-center justify-center gap-2 text-sm text-slate-500" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" aria-hidden />
      {label}
    </div>
  );
}
