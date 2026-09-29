import { useMemo, useState } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip } from "react-leaflet";
import type { LatLngBoundsExpression } from "leaflet";
import "leaflet/dist/leaflet.css";

import { ACTION_STYLE, NOT_MODELED_HEX, humanize, pct } from "../lib/format";
import type { Action, DecisionSummary } from "../types";
import { STATUS_STYLE } from "./StatusBadge";

const PENDING_HEX = "#b45309"; // amber-700 dashed outline

interface Props {
  summaries: DecisionSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export default function PanchayatMap({ summaries, selectedId, onSelect }: Props) {
  const bounds = useMemo<LatLngBoundsExpression>(() => {
    const lats = summaries.map((s) => s.panchayat.lat);
    const lons = summaries.map((s) => s.panchayat.lon);
    return [
      [Math.min(...lats), Math.min(...lons)],
      [Math.max(...lats), Math.max(...lons)],
    ];
  }, [summaries]);

  // Later markers draw on top: unmodelled first, then coloured, then the selection.
  const ordered = useMemo(() => {
    const layer = (s: DecisionSummary) => (s.panchayat.id === selectedId ? 2 : s.action ? 1 : 0);
    return [...summaries].sort((a, b) => layer(a) - layer(b));
  }, [summaries, selectedId]);

  // Background tiles come from OpenStreetMap; markers work without them.
  const [tilesFailing, setTilesFailing] = useState(false);

  return (
    <div className="relative h-full w-full">
      {tilesFailing && (
        <div className="absolute right-3 top-3 z-[1000] max-w-xs rounded-md bg-white/95 px-3 py-2 text-xs text-slate-600 shadow ring-1 ring-slate-900/10">
          Map background couldn’t load (offline?). Markers and details still work.
        </div>
      )}
      <MapContainer bounds={bounds} boundsOptions={{ padding: [40, 40] }} className="h-full w-full" scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          eventHandlers={{ tileerror: () => setTilesFailing(true), tileload: () => setTilesFailing(false) }}
        />
        {ordered.map((s) => {
          const selected = s.panchayat.id === selectedId;
          const fill = s.action ? ACTION_STYLE[s.action].hex : "#ffffff";
          const pending = s.status === "needs_officer_review";
          return (
            <CircleMarker
              key={s.panchayat.id}
              center={[s.panchayat.lat, s.panchayat.lon]}
              radius={selected ? 11 : pending ? 8 : 7}
              pathOptions={{
                color: selected ? "#0f172a" : pending ? PENDING_HEX : s.action ? "#ffffff" : NOT_MODELED_HEX,
                weight: selected ? 3 : pending ? 2.5 : 2,
                dashArray: pending && !selected ? "3 2" : undefined,
                fillColor: fill,
                fillOpacity: s.action ? 0.95 : 0.9,
              }}
              eventHandlers={{ click: () => onSelect(s.panchayat.id) }}
            >
              <Tooltip direction="top" offset={[0, -6]}>
                <div className="text-xs">
                  <div className="font-semibold">
                    {s.panchayat.name} <span className="font-normal text-slate-500">· {s.panchayat.block_name}</span>
                  </div>
                  <div>
                    {humanize(s.crop)} ·{" "}
                    {s.action ? (
                      <>
                        <b>{ACTION_STYLE[s.action].label}</b> ({pct(s.confidence ?? 0)} conf.)
                        {s.status && s.status !== "auto_approved" && (
                          <div className="text-slate-600">{STATUS_STYLE[s.status].label}</div>
                        )}
                      </>
                    ) : (
                      <span className="text-slate-500">crop not modelled</span>
                    )}
                  </div>
                </div>
              </Tooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>
      <Legend summaries={summaries} />
    </div>
  );
}

function Legend({ summaries }: { summaries: DecisionSummary[] }) {
  const counts = new Map<Action | null, number>();
  for (const s of summaries) counts.set(s.action, (counts.get(s.action) ?? 0) + 1);
  const pending = summaries.filter((s) => s.status === "needs_officer_review").length;

  return (
    <div className="absolute bottom-6 left-3 z-[1000] rounded-lg bg-white/95 px-3 py-2 text-xs shadow-md ring-1 ring-slate-900/10">
      <div className="mb-1 font-semibold text-slate-700">Action (after officer review)</div>
      <ul className="space-y-0.5">
        {(Object.keys(ACTION_STYLE) as Action[]).map((a) => (
          <li key={a} className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full ring-1 ring-white" style={{ background: ACTION_STYLE[a].hex }} />
            <span className="flex-1 text-slate-700">{ACTION_STYLE[a].label}</span>
            <span className="tabular-nums text-slate-500">{counts.get(a) ?? 0}</span>
          </li>
        ))}
        <li className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full border-2 bg-white" style={{ borderColor: NOT_MODELED_HEX }} />
          <span className="flex-1 text-slate-500">Crop not modelled</span>
          <span className="tabular-nums text-slate-500">{counts.get(null) ?? 0}</span>
        </li>
        <li className="mt-1 flex items-center gap-2 border-t border-slate-200 pt-1">
          <span
            className="h-3 w-3 rounded-full border-2 border-dashed bg-slate-200"
            style={{ borderColor: PENDING_HEX }}
          />
          <span className="flex-1 text-slate-700">Awaiting officer review</span>
          <span className="tabular-nums text-slate-500">{pending}</span>
        </li>
      </ul>
    </div>
  );
}
