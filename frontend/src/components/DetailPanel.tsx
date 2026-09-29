import { useState } from "react";
import { Link } from "react-router";

import { getDecision, getForecast, getTwin } from "../api";
import { humanize } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { MODELED_CROPS, type Crop, type DecisionSummary } from "../types";
import EscalationBanner from "./panel/EscalationBanner";
import ForecastSection from "./panel/ForecastSection";
import LossTable from "./panel/LossTable";
import MessageSection from "./panel/MessageSection";
import ScenarioSection from "./panel/ScenarioSection";
import ScoresSection from "./panel/ScoresSection";
import Section, { ErrorNote, Skeleton } from "./panel/Section";

interface Props {
  summary: DecisionSummary;
  onClose: () => void;
  onOpenQueue: () => void;
  /** Changes after an officer review, to refetch the decision. */
  version: number;
}

/** Mount with `key={panchayat id}` so the crop choice resets per panchayat. */
export default function DetailPanel({ summary, onClose, onOpenQueue, version }: Props) {
  const p = summary.panchayat;
  const [crop, setCrop] = useState<Crop | null>(summary.modeled ? summary.crop : null);

  const forecast = useAsync((signal) => getForecast(p.id, signal), [p.id]);
  const analysis = useAsync(
    async (signal) => {
      if (!crop) return null;
      const [twin, decision] = await Promise.all([getTwin(p.id, crop, signal), getDecision(p.id, crop, signal)]);
      return { twin, decision };
    },
    [p.id, crop, version],
  );

  return (
    <div className="flex h-full flex-col">
      <header className="px-5 pb-3 pt-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-[11px] font-medium uppercase tracking-wider text-slate-400">{p.id}</div>
            <h2 className="text-lg font-semibold leading-tight text-slate-900">{p.name}</h2>
            <div className="text-sm text-slate-500">
              {p.block_name} block · {p.district}
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Link
              to={`/farmer/${p.id}`}
              target="_blank"
              className="rounded-md px-2 py-1 text-xs font-medium text-sky-700 hover:bg-sky-50"
              title="Open the farmer's mobile screen for this panchayat"
            >
              Farmer view ↗
            </Link>
            <button
              onClick={onClose}
              className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              aria-label="Close panel"
            >
              ✕
            </button>
          </div>
        </div>

        <dl className="mt-3 grid grid-cols-3 gap-2 text-xs">
          <Fact label="Soil" value={humanize(p.soil_type)} />
          <Fact label="Irrigation" value={humanize(p.irrigation_type)} />
          <Fact label="Primary crop" value={humanize(p.primary_crop)} />
        </dl>

        <label className="mt-3 flex items-center gap-2 text-xs text-slate-600">
          <span>Analyse for</span>
          <select
            value={crop ?? ""}
            onChange={(e) => setCrop((e.target.value || null) as Crop | null)}
            className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800 focus:border-sky-500 focus:outline-none"
          >
            {!summary.modeled && <option value="">Select a crop…</option>}
            {MODELED_CROPS.map((c) => (
              <option key={c} value={c}>
                {humanize(c)}
                {c === p.primary_crop ? " (primary)" : ""}
              </option>
            ))}
          </select>
          {crop && crop !== summary.crop && summary.modeled && (
            <span className="text-[11px] text-amber-700">Map colour uses {humanize(summary.crop)}</span>
          )}
        </label>
      </header>

      <div className="flex-1 overflow-y-auto">
        {!crop ? (
          <>
            <Section title="Decision">
              <p className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
                No crop-response model for <b>{humanize(p.primary_crop)}</b> yet. Pick cotton, soybean or paddy above to
                run the twin and decision for this panchayat.
              </p>
            </Section>
            <MessageSection panchayatId={p.id} primaryCrop={p.primary_crop} selectedCrop={crop} version={version} />
          </>
        ) : analysis.status === "loading" ? (
          <Section title="Model recommendation">
            <Skeleton rows={6} />
          </Section>
        ) : analysis.status === "error" ? (
          <Section title="Model recommendation">
            <ErrorNote message={analysis.error.message} onRetry={analysis.reload} />
          </Section>
        ) : (
          analysis.data && (
            <>
              <EscalationBanner
                escalation={analysis.data.decision.escalation}
                inQueue={summary.modeled && crop === summary.crop}
                onOpenQueue={onOpenQueue}
              />
              <ScoresSection decision={analysis.data.decision} />
              <MessageSection panchayatId={p.id} primaryCrop={p.primary_crop} selectedCrop={crop} version={version} />
              <LossTable decision={analysis.data.decision} />
              <ScenarioSection twin={analysis.data.twin} />
            </>
          )
        )}

        {forecast.status === "loading" ? (
          <Section title="4-week rainfall forecast">
            <Skeleton rows={4} />
          </Section>
        ) : forecast.status === "error" ? (
          <Section title="4-week rainfall forecast">
            <ErrorNote message={forecast.error.message} onRetry={forecast.reload} />
          </Section>
        ) : (
          <ForecastSection forecast={forecast.data} />
        )}
      </div>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-slate-50 px-2 py-1.5">
      <dt className="text-[10px] text-slate-500">{label}</dt>
      <dd className="font-medium text-slate-800">{value}</dd>
    </div>
  );
}
