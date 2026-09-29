import { useEffect, useId, useState, type ReactNode } from "react";
import { useParams } from "react-router";

import { ApiError, getDecision, getForecast } from "../api";
import VoiceNoteButton from "../components/farmer/VoiceNoteButton";
import { ACTION_COPY, chanceInTen, cropName, greeting, rainWords, whyPoints, type WhyPoint } from "../lib/farmerCopy";
import { useAsync } from "../lib/useAsync";
import type { DecisionResponse, ForecastResponse, Panchayat } from "../types";

const TONE_STYLE = {
  go: { band: "bg-emerald-600", icon: <CheckIcon />, soft: "bg-emerald-50" },
  wait: { band: "bg-amber-500", icon: <ClockIcon />, soft: "bg-amber-50" },
  caution: { band: "bg-red-600", icon: <ShieldIcon />, soft: "bg-red-50" },
  check: { band: "bg-sky-600", icon: <RefreshIcon />, soft: "bg-sky-50" },
} as const;

export default function FarmerPage() {
  const { panchayatId = "" } = useParams();

  // The forecast also tells us the panchayat and works for every crop.
  const forecast = useAsync((signal) => getForecast(panchayatId, signal), [panchayatId]);
  // 422 = no advice model for this crop yet; handled as a normal state, not an error.
  const decision = useAsync(
    (signal) =>
      getDecision(panchayatId, undefined, signal).catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 422) return null;
        throw e;
      }),
    [panchayatId],
  );

  if (forecast.status === "error") {
    const notFound = forecast.error instanceof ApiError && forecast.error.status === 404;
    return (
      <Screen>
        <Message
          title={notFound ? "Village not found" : "Can’t load advice right now"}
          text={notFound ? "Please check the link you were sent." : connectionHint()}
          onRetry={
            notFound
              ? undefined
              : () => {
                  forecast.reload();
                  decision.reload();
                }
          }
        />
      </Screen>
    );
  }
  if (forecast.status === "loading" || decision.status === "loading") {
    return (
      <Screen>
        <LoadingCard />
      </Screen>
    );
  }

  const p = forecast.data.panchayat;
  return (
    <Screen>
      <Greeting panchayat={p} />
      {decision.status === "error" ? (
        <Message title="Can’t load advice right now" text={connectionHint()} onRetry={decision.reload} />
      ) : decision.data ? (
        <>
          <AdviceCard decision={decision.data} />
          <WhySection points={whyPoints(decision.data, forecast.data)} />
        </>
      ) : (
        <NoAdviceCard panchayat={p} forecast={forecast.data} />
      )}
    </Screen>
  );
}

function Screen({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh bg-stone-100 text-slate-900">
      <div className="mx-auto flex min-h-dvh max-w-md flex-col gap-4 px-4 pb-8 pt-5 text-[17px] leading-relaxed">
        <div className="flex items-center gap-2 text-sm font-semibold text-emerald-800">
          <RainIcon />
          Monsoon advice
        </div>
        {children}
        <p className="mt-auto pt-4 text-center text-xs leading-snug text-slate-500">
          Demo version using sample weather data. Talk to your Krishi Sahayak before big decisions.
        </p>
      </div>
    </div>
  );
}

function Greeting({ panchayat }: { panchayat: Panchayat }) {
  const today = new Intl.DateTimeFormat("en-IN", { weekday: "long", day: "numeric", month: "long" }).format(new Date());
  useEffect(() => {
    document.title = `Monsoon advice · ${panchayat.name}`;
  }, [panchayat.name]);

  return (
    <header>
      <h1 className="text-2xl font-bold">Namaste 🙏</h1>
      <p className="text-slate-600">
        {greeting()}! Here is today’s advice for {panchayat.name}.
      </p>
      <p className="text-sm text-slate-500">{today}</p>
    </header>
  );
}

function AdviceCard({ decision }: { decision: DecisionResponse }) {
  // Final action = the officer's override if there is one.
  const copy = ACTION_COPY[decision.escalation.final_action];
  const tone = TONE_STYLE[copy.tone];
  const crop = cropName(decision.crop);
  const status = decision.escalation.status;

  return (
    <article className="overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-slate-900/5">
      <div className={`flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white ${tone.band}`}>
        {tone.icon}
        Today’s advice for your {crop}
      </div>
      <div className="space-y-4 p-5">
        {status === "needs_officer_review" && (
          <p className="rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-900">
            Your agriculture officer is checking this advice. It may change.
          </p>
        )}
        {(status === "approved" || status === "overridden") && (
          <p className="flex items-center gap-1.5 text-sm font-medium text-emerald-800">
            <CheckIcon />
            {status === "overridden" ? "Updated by your agriculture officer" : "Checked by your agriculture officer"}
          </p>
        )}
        <h2 className="text-[1.65rem] font-bold leading-tight">{copy.headline(crop)}</h2>
        <p className="text-slate-700">{copy.body(crop)}</p>
        <ul className={`space-y-2 rounded-2xl p-4 ${tone.soft}`}>
          {copy.steps.map((step) => (
            <li key={step} className="flex gap-2.5">
              <span className={`mt-2.5 h-2 w-2 shrink-0 rounded-full ${tone.band}`} aria-hidden />
              <span>{step}</span>
            </li>
          ))}
        </ul>
        <VoiceNoteButton />
      </div>
    </article>
  );
}

function NoAdviceCard({ panchayat, forecast }: { panchayat: Panchayat; forecast: ForecastResponse }) {
  const w1 = forecast.weeks[0];
  return (
    <article className="space-y-3 rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-900/5">
      <h2 className="text-xl font-bold leading-tight">Advice for {cropName(panchayat.primary_crop)} is coming soon</h2>
      <p className="text-slate-700">Meanwhile, here is this week’s weather:</p>
      <p className="rounded-2xl bg-sky-50 p-4">
        Expect <b>{rainWords(w1.rainfall_mm.p50)}</b> (about {Math.round(w1.rainfall_mm.p50)} mm). Chance of 5 or more
        dry days in a row: <b>{chanceInTen(w1.dry_spell_probability)}</b>.
      </p>
      <VoiceNoteButton />
    </article>
  );
}

function WhySection({ points }: { points: WhyPoint[] }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  return (
    <section className="rounded-3xl bg-white shadow-sm ring-1 ring-slate-900/5">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={panelId}
        className="flex min-h-14 w-full items-center justify-between gap-3 px-5 py-3 text-left text-lg font-semibold"
      >
        Why this advice?
        <svg
          viewBox="0 0 24 24"
          className={`h-6 w-6 shrink-0 text-slate-500 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          aria-hidden
        >
          <path d="m6 9 6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <ul id={panelId} className="space-y-4 border-t border-slate-100 px-5 pb-5 pt-4">
          {points.map((pt) => (
            <li key={pt.title}>
              <div className="font-semibold">{pt.title}</div>
              <p className="text-slate-700">{pt.text}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Message({ title, text, onRetry }: { title: string; text: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-900/5">
      <h2 className="text-xl font-bold">{title}</h2>
      <p className="mt-1 text-slate-600">{text}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 min-h-12 w-full rounded-2xl bg-slate-900 px-4 py-3 text-base font-semibold text-white active:bg-slate-700"
        >
          Try again
        </button>
      )}
    </div>
  );
}

function connectionHint(): string {
  return typeof navigator !== "undefined" && !navigator.onLine
    ? "You seem to be offline. Connect to the internet and try again."
    : "Please check your internet and try again.";
}

function LoadingCard() {
  return (
    <div className="animate-pulse space-y-4" aria-label="Loading">
      <div className="h-8 w-3/4 rounded-lg bg-stone-200" />
      <div className="h-72 rounded-3xl bg-white" />
      <div className="h-14 rounded-3xl bg-white" />
    </div>
  );
}

// --- Icons (inline so the screen works without an icon library) ---
const iconProps = {
  viewBox: "0 0 24 24",
  className: "h-5 w-5",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2.2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
} as const;

function CheckIcon() {
  return (
    <svg {...iconProps}>
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}
function ClockIcon() {
  return (
    <svg {...iconProps}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}
function ShieldIcon() {
  return (
    <svg {...iconProps}>
      <path d="M12 3 4 6v6c0 4.5 3.4 8.3 8 9 4.6-.7 8-4.5 8-9V6l-8-3Z" />
    </svg>
  );
}
function RefreshIcon() {
  return (
    <svg {...iconProps}>
      <path d="M20 11a8 8 0 0 0-14.9-3M4 4v4h4M4 13a8 8 0 0 0 14.9 3M20 20v-4h-4" />
    </svg>
  );
}
function RainIcon() {
  return (
    <svg {...iconProps}>
      <path d="M7 15a4 4 0 0 1-.6-8A6 6 0 0 1 18 8a3.5 3.5 0 0 1 0 7" />
      <path d="M9 18v2M13 17v3M17 18v2" />
    </svg>
  );
}
