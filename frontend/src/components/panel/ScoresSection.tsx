import { ACTION_STYLE, humanize, pct } from "../../lib/format";
import type { DecisionResponse } from "../../types";
import Section from "./Section";

const RATING_STYLE = {
  high: "text-teal-700",
  moderate: "text-slate-700",
  low: "text-orange-700",
} as const;

/**
 * Recommendation plus the two scores. Confidence and suitability answer different
 * questions, so they are shown side by side on different scales and never merged.
 */
export default function ScoresSection({ decision }: { decision: DecisionResponse }) {
  const { recommendation: rec, crop_suitability: suit } = decision;
  const style = ACTION_STYLE[rec.action];

  return (
    <Section title="Model recommendation">
      <div className="flex items-start gap-3">
        <span className={`shrink-0 rounded-md px-2.5 py-1 text-sm font-bold ring-1 ring-inset ${style.badge}`}>
          {rec.action}
        </span>
        <p className="text-sm leading-snug text-slate-700">{rec.rationale}</p>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        {/* Confidence: about this forecast and this decision. */}
        <div className="rounded-lg border border-slate-200 p-3">
          <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">Decision confidence</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{pct(rec.confidence)}</div>
          <Meter value={rec.confidence} className={style.bar} />
          <p className="mt-2 text-[11px] leading-snug text-slate-500">{rec.confidence_basis}.</p>
        </div>

        {/* Suitability: long-term agronomic fit, ignores the forecast. */}
        <div className="rounded-lg border border-slate-200 p-3">
          <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">Crop suitability</div>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="text-2xl font-semibold tabular-nums text-slate-900">{suit.score}</span>
            <span className="text-xs text-slate-400">/ 100</span>
            <span className={`ml-auto text-xs font-medium capitalize ${RATING_STYLE[suit.rating]}`}>{suit.rating}</span>
          </div>
          <dl className="mt-2 space-y-1 text-[11px] text-slate-600">
            <SubScore label={`Soil · ${humanize(suit.soil_type)}`} value={suit.soil_score} />
            <SubScore label={`Water · ${humanize(suit.irrigation_type)}`} value={suit.water_score} />
          </dl>
          <p className="mt-2 text-[11px] leading-snug text-slate-500">
            Normal Jun–Sep rain {suit.season_normal_rainfall_mm} mm; {humanize(decision.crop)} does best with{" "}
            {suit.crop_water_range_mm[0]}–{suit.crop_water_range_mm[1]} mm.
          </p>
        </div>
      </div>
      <p className="mt-2 text-center text-[11px] text-slate-400">
        Separate measures: confidence reflects this forecast; suitability reflects soil and climate. They are not
        combined.
      </p>
    </Section>
  );
}

function Meter({ value, className }: { value: number; className: string }) {
  return (
    <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
      <div className={`h-full rounded-full ${className}`} style={{ width: `${value * 100}%` }} />
    </div>
  );
}

function SubScore({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex justify-between">
        <dt>{label}</dt>
        <dd className="tabular-nums">{value}</dd>
      </div>
      <div className="mt-0.5 h-1 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-teal-500" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}
