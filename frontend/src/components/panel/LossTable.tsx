import { ACTION_STYLE, SCENARIO_STYLE, inr, pct } from "../../lib/format";
import type { DecisionResponse } from "../../types";
import Section from "./Section";

export default function LossTable({ decision }: { decision: DecisionResponse }) {
  const rows = decision.expected_loss_table;
  const scenarios = rows[0].by_scenario;
  const maxLoss = Math.max(...rows.map((r) => r.expected_loss_inr_per_ha));
  const recommended = decision.recommendation.action;

  return (
    <Section title="Expected loss by action" aside="₹ per hectare">
      <div className="-mx-1 overflow-x-auto">
        <table className="w-full min-w-[26rem] text-xs">
          <thead>
            <tr className="text-left text-[11px] text-slate-500">
              <th className="px-1 pb-1.5 font-medium">Action</th>
              <th className="px-1 pb-1.5 font-medium">Expected loss</th>
              {scenarios.map((s) => (
                <th key={s.scenario} className="px-1 pb-1.5 text-right font-medium">
                  <div className="flex items-center justify-end gap-1">
                    <span className={`h-2 w-2 rounded-full ${SCENARIO_STYLE[s.scenario].dot}`} />
                    {SCENARIO_STYLE[s.scenario].label}
                  </div>
                  <div className="font-normal tabular-nums text-slate-400">p={pct(s.probability)}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const isRec = r.action === recommended;
              return (
                <tr key={r.action} className={isRec ? "bg-slate-50 font-medium" : ""} title={r.description}>
                  <td className="rounded-l px-1 py-1.5">
                    <span className="flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: ACTION_STYLE[r.action].hex }} />
                      {r.action}
                      {isRec && <span className="text-[10px] font-normal text-slate-400">★</span>}
                    </span>
                  </td>
                  <td className="min-w-[5.5rem] px-1 py-1.5">
                    <div className="tabular-nums">{inr(r.expected_loss_inr_per_ha)}</div>
                    <div className="mt-1 h-1 rounded-full bg-slate-100">
                      <div
                        className={`h-full rounded-full ${isRec ? ACTION_STYLE[r.action].bar : "bg-slate-300"}`}
                        style={{ width: `${(r.expected_loss_inr_per_ha / maxLoss) * 100}%` }}
                      />
                    </div>
                  </td>
                  {r.by_scenario.map((s) => (
                    <td key={s.scenario} className="px-1 py-1.5 text-right tabular-nums text-slate-600 last:rounded-r">
                      {inr(s.cost_if_wrong_inr_per_ha)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-[11px] text-slate-400">
        Scenario columns show the cost if that scenario happens. Expected loss = Σ probability × cost. ★ = lowest
        expected loss.
      </p>
    </Section>
  );
}
