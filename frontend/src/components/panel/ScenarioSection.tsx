import { SCENARIO_STYLE, humanize, inr, inrSigned, pct, signedPct } from "../../lib/format";
import type { TwinResponse } from "../../types";
import Section from "./Section";

export default function ScenarioSection({ twin }: { twin: TwinResponse }) {
  const { economics: econ, summary } = twin;

  return (
    <Section
      title="Twin scenarios"
      aside={`${humanize(econ.crop)} · ${econ.normal_yield_q_per_ha} q/ha @ ${inr(econ.price_inr_per_q)}/q`}
    >
      {/* Probability split across scenarios */}
      <div className="flex h-5 overflow-hidden rounded-md text-[10px] font-medium text-white">
        {twin.scenarios.map((s) =>
          s.probability > 0 ? (
            <div
              key={s.scenario}
              className={`${SCENARIO_STYLE[s.scenario].bar} flex items-center justify-center overflow-hidden`}
              style={{ width: `${s.probability * 100}%` }}
              title={`${s.label}: ${pct(s.probability)}`}
            >
              {s.probability >= 0.1 && pct(s.probability)}
            </div>
          ) : null,
        )}
      </div>

      <table className="mt-3 w-full text-xs">
        <thead>
          <tr className="text-left text-[11px] text-slate-500">
            <th className="pb-1.5 font-medium">Scenario</th>
            <th className="pb-1.5 text-right font-medium">Prob.</th>
            <th className="pb-1.5 text-right font-medium">Yield</th>
            <th className="pb-1.5 text-right font-medium">Extra cost</th>
            <th className="pb-1.5 text-right font-medium">E[profit]</th>
            <th className="pb-1.5 text-right font-medium" title="Shortfall of a 1-in-10 bad outcome vs a normal season">
              Downside
            </th>
          </tr>
        </thead>
        <tbody className="tabular-nums">
          {twin.scenarios.map((s) => (
            <tr key={s.scenario} className="border-t border-slate-100" title={s.description}>
              <td className="py-1.5">
                <span className="flex items-center gap-1.5">
                  <span className={`h-2 w-2 rounded-full ${SCENARIO_STYLE[s.scenario].dot}`} />
                  {s.label}
                </span>
              </td>
              <td className="py-1.5 text-right font-medium">{pct(s.probability)}</td>
              <td className={`py-1.5 text-right ${s.yield_impact_pct < 0 ? "text-red-600" : "text-slate-600"}`}>
                {signedPct(s.yield_impact_pct)}
              </td>
              <td className="py-1.5 text-right text-slate-600">{inrSigned(s.cost_impact_inr_per_ha)}</td>
              <td className={`py-1.5 text-right ${s.expected_profit_inr_per_ha < 0 ? "text-red-600" : ""}`}>
                {inr(s.expected_profit_inr_per_ha)}
              </td>
              <td className="py-1.5 text-right text-slate-600">{inr(s.downside_risk_inr_per_ha)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <dl className="mt-3 grid grid-cols-3 gap-2 text-xs">
        <Stat label="Normal-season profit" value={inr(summary.baseline_profit_inr_per_ha)} />
        <Stat label="Expected profit" value={inr(summary.expected_profit_inr_per_ha)} />
        <Stat
          label="Change"
          value={inrSigned(summary.expected_change_inr_per_ha)}
          tone={summary.expected_change_inr_per_ha < 0 ? "text-red-600" : "text-emerald-700"}
        />
      </dl>
    </Section>
  );
}

function Stat({ label, value, tone = "text-slate-900" }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-md bg-slate-50 px-2 py-1.5">
      <dt className="text-[10px] text-slate-500">{label}</dt>
      <dd className={`font-semibold tabular-nums ${tone}`}>{value}</dd>
    </div>
  );
}
