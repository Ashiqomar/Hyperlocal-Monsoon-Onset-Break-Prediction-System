import { pct, shortDate } from "../../lib/format";
import type { ForecastResponse } from "../../types";
import Section from "./Section";

export default function ForecastSection({ forecast }: { forecast: ForecastResponse }) {
  const { weeks, definitions: def } = forecast;
  const scaleMax = Math.max(...weeks.map((w) => w.rainfall_mm.p90), 1);

  return (
    <Section title="4-week rainfall forecast" aside={`${forecast.ensemble_members}-member ensemble`}>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-[11px] text-slate-500">
            <th className="pb-1.5 font-medium">Week</th>
            <th className="pb-1.5 font-medium">
              Rainfall <span className="font-normal text-slate-400">P10–P90 · P50</span>
            </th>
            <th className="pb-1.5 text-right font-medium">Dry spell</th>
            <th className="pb-1.5 text-right font-medium">Heavy rain</th>
          </tr>
        </thead>
        <tbody className="tabular-nums">
          {weeks.map((w) => {
            const { p10, p50, p90 } = w.rainfall_mm;
            return (
              <tr key={w.week} className="border-t border-slate-100">
                <td className="py-2 pr-2 align-top">
                  <div className="font-medium">W{w.week}</div>
                  <div className="whitespace-nowrap text-[10px] text-slate-400">
                    {shortDate(w.start_date)}–{shortDate(w.end_date)}
                  </div>
                </td>
                <td className="w-full py-2 pr-3">
                  <div className="relative h-2.5 rounded-full bg-slate-100">
                    <div
                      className="absolute h-full rounded-full bg-sky-200"
                      style={{ left: `${(p10 / scaleMax) * 100}%`, width: `${((p90 - p10) / scaleMax) * 100}%` }}
                    />
                    <div
                      className="absolute -top-0.5 h-3.5 w-0.5 rounded bg-sky-700"
                      style={{ left: `${(p50 / scaleMax) * 100}%` }}
                    />
                  </div>
                  <div className="mt-1 flex justify-between text-[10px] text-slate-500">
                    <span>
                      {p10.toFixed(0)}–{p90.toFixed(0)} mm
                    </span>
                    <span className="font-medium text-sky-800">P50 {p50.toFixed(0)} mm</span>
                  </div>
                </td>
                <ProbCell value={w.dry_spell_probability} tone="bg-orange-400" />
                <ProbCell value={w.heavy_rain_probability} tone="bg-blue-500" />
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-2 text-[11px] text-slate-400">
        Dry spell: ≥{def.dry_spell_min_days} consecutive days &lt; {def.dry_day_threshold_mm} mm within the week. Heavy
        rain: any day ≥ {def.heavy_rain_threshold_mm} mm.
      </p>
    </Section>
  );
}

function ProbCell({ value, tone }: { value: number; tone: string }) {
  return (
    <td className="py-2 pl-2 text-right align-top">
      <div className="font-medium">{pct(value)}</div>
      <div className="ml-auto mt-1 h-1 w-12 rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${value * 100}%` }} />
      </div>
    </td>
  );
}
