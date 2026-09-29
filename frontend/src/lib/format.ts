import type { Action, Scenario } from "../types";

// Marker/badge colours. Hex values are used by Leaflet; class names by Tailwind.
export const ACTION_STYLE: Record<Action, { hex: string; label: string; badge: string; bar: string }> = {
  SOW: {
    hex: "#10b981",
    label: "Sow",
    badge: "bg-emerald-100 text-emerald-800 ring-emerald-600/20",
    bar: "bg-emerald-500",
  },
  WAIT: { hex: "#f59e0b", label: "Wait", badge: "bg-amber-100 text-amber-800 ring-amber-600/20", bar: "bg-amber-500" },
  SPRAY: {
    hex: "#ef4444",
    label: "Spray (caution)",
    badge: "bg-red-100 text-red-800 ring-red-600/20",
    bar: "bg-red-500",
  },
  REASSESS: { hex: "#0ea5e9", label: "Reassess", badge: "bg-sky-100 text-sky-800 ring-sky-600/20", bar: "bg-sky-500" },
};
export const NOT_MODELED_HEX = "#94a3b8";

export const SCENARIO_STYLE: Record<Scenario, { label: string; bar: string; dot: string }> = {
  normal: { label: "Normal", bar: "bg-emerald-400", dot: "bg-emerald-400" },
  dry: { label: "Dry", bar: "bg-orange-400", dot: "bg-orange-400" },
  wet: { label: "Wet", bar: "bg-blue-500", dot: "bg-blue-500" },
  false_onset: { label: "False onset", bar: "bg-purple-400", dot: "bg-purple-400" },
};

const inrFormatter = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

/** ₹ with Indian digit grouping, e.g. ₹1,23,456. */
export const inr = (value: number) => `${value < 0 ? "−" : ""}₹${inrFormatter.format(Math.abs(value))}`;

/** Signed ₹, e.g. +₹4,000 / −₹2,638. */
export const inrSigned = (value: number) => (value > 0 ? `+${inr(value)}` : inr(value));

export const pct = (p: number, digits = 0) => `${(p * 100).toFixed(digits)}%`;

export const signedPct = (value: number) => `${value > 0 ? "+" : ""}${value.toFixed(0)}%`;

/** "deep_black" -> "Deep black" */
export const humanize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1).replaceAll("_", " ");

const dateFormatter = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short" });
export const shortDate = (iso: string) => dateFormatter.format(new Date(`${iso}T00:00:00`));
