import { useEffect, useState } from "react";

/**
 * Placeholder voice-note player. There is no audio yet: it only simulates
 * play / pause / finished states and progress so the UI can be tested.
 */
const DURATION_S = 20;

type PlayState = "idle" | "playing" | "paused" | "done";

export default function VoiceNoteButton() {
  const [state, setState] = useState<PlayState>("idle");
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (state !== "playing") return;
    // Measure real time rather than counting ticks: browsers throttle timers
    // when the screen is locked or the tab is in the background.
    const startedAt = performance.now() - elapsed * 1000;
    const id = window.setInterval(() => {
      const t = (performance.now() - startedAt) / 1000;
      if (t >= DURATION_S) {
        setElapsed(DURATION_S);
        setState("done");
      } else {
        setElapsed(t);
      }
    }, 250);
    return () => window.clearInterval(id);
    // `elapsed` is read only when playback (re)starts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state]);

  const toggle = () => {
    if (state === "playing") return setState("paused");
    if (state === "done") setElapsed(0);
    setState("playing");
  };

  const playing = state === "playing";
  const label =
    state === "playing"
      ? "Pause voice note"
      : state === "paused"
        ? "Resume voice note"
        : state === "done"
          ? "Play again"
          : "Listen to voice note";

  return (
    <div>
      <button
        type="button"
        onClick={toggle}
        aria-pressed={playing}
        className="flex min-h-14 w-full items-center gap-3 rounded-2xl bg-slate-900 px-4 py-3 text-left text-white active:scale-[0.99] active:bg-slate-800"
      >
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/15">
          {playing ? <PauseIcon /> : <PlayIcon />}
        </span>
        <span className="flex-1">
          <span className="block text-base font-semibold">{label}</span>
          <span className="block text-sm text-slate-300">
            {state === "idle" ? `${DURATION_S} seconds` : `${fmt(elapsed)} / ${fmt(DURATION_S)}`}
          </span>
        </span>
        {playing && <Equaliser />}
      </button>

      {state !== "idle" && (
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-200" aria-hidden>
          <div
            className="h-full rounded-full bg-slate-900 transition-[width] duration-200"
            style={{ width: `${(elapsed / DURATION_S) * 100}%` }}
          />
        </div>
      )}
      <p className="mt-1.5 text-center text-xs text-slate-400" aria-live="polite">
        {playing ? "Playing (demo, no sound yet)" : "Voice notes are coming soon"}
      </p>
    </div>
  );
}

const fmt = (s: number) => `0:${String(Math.floor(s)).padStart(2, "0")}`;

function PlayIcon() {
  return (
    <svg viewBox="0 0 24 24" className="ml-0.5 h-5 w-5 fill-current" aria-hidden>
      <path d="M8 5.5v13a1 1 0 0 0 1.5.86l10.5-6.5a1 1 0 0 0 0-1.72L9.5 4.64A1 1 0 0 0 8 5.5Z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5 fill-current" aria-hidden>
      <rect x="6" y="5" width="4" height="14" rx="1" />
      <rect x="14" y="5" width="4" height="14" rx="1" />
    </svg>
  );
}

function Equaliser() {
  return (
    <span className="flex h-6 items-end gap-0.5" aria-hidden>
      {[0, 150, 300, 450].map((delay) => (
        <span
          key={delay}
          className="w-1 animate-pulse rounded-full bg-emerald-400"
          style={{ height: `${40 + ((delay / 150) % 3) * 20}%`, animationDelay: `${delay}ms` }}
        />
      ))}
    </span>
  );
}
