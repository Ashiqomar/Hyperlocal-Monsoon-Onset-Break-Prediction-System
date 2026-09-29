import { useState, type ReactNode } from "react";

import { getNotifyPreview, sendNotify } from "../../api";
import { humanize } from "../../lib/format";
import { useAsync } from "../../lib/useAsync";
import type { Crop } from "../../types";
import Section, { ErrorNote, Skeleton } from "./Section";

interface Props {
  panchayatId: string;
  primaryCrop: Crop;
  /** Crop picked in the panel; messages always use the primary crop. */
  selectedCrop: Crop | null;
  /** Changes after an officer review, to rebuild the preview. */
  version: number;
}

type SendState =
  { kind: "idle" } | { kind: "sending" } | { kind: "logged"; at: string } | { kind: "error"; message: string };

export default function MessageSection({ panchayatId, primaryCrop, selectedCrop, version }: Props) {
  const preview = useAsync((signal) => getNotifyPreview(panchayatId, signal), [panchayatId, version]);
  const [send, setSend] = useState<SendState>({ kind: "idle" });
  const [copied, setCopied] = useState(false);

  if (preview.status === "loading") {
    return (
      <Section title="WhatsApp message">
        <Skeleton rows={4} />
      </Section>
    );
  }
  if (preview.status === "error") {
    return (
      <Section title="WhatsApp message">
        <ErrorNote message={preview.error.message} onRetry={preview.reload} />
      </Section>
    );
  }

  const msg = preview.data;

  const onSend = async () => {
    setSend({ kind: "sending" });
    try {
      const res = await sendNotify(panchayatId);
      setSend({ kind: "logged", at: res.delivery.logged_at });
    } catch (e) {
      setSend({ kind: "error", message: e instanceof Error ? e.message : String(e) });
    }
  };

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(msg.text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard can be unavailable (e.g. non-secure context); the text is selectable anyway.
    }
  };

  return (
    <Section title="WhatsApp message" aside={`${msg.char_count} chars · English`}>
      {selectedCrop && selectedCrop !== primaryCrop && (
        <p className="mb-2 text-[11px] text-amber-700">
          Farmer messages use the primary crop ({humanize(primaryCrop)}), not the crop picked above.
        </p>
      )}

      {/* Chat-style preview */}
      <div className="rounded-lg bg-[#efeae2] p-3">
        <div className="ml-auto max-w-[92%] rounded-lg rounded-tr-none bg-[#d9fdd3] px-3 py-2 text-[13px] leading-snug text-slate-900 shadow-sm">
          <div className="whitespace-pre-wrap break-words">{formatWhatsApp(msg.text)}</div>
          <div className="mt-1 text-right text-[10px] text-slate-500">preview</div>
        </div>
      </div>

      <ul className="mt-2 space-y-1 text-[11px] text-slate-500">
        {msg.translations.map((t) => (
          <li key={t.language} className="flex items-center gap-1.5">
            <span className="rounded bg-slate-100 px-1.5 py-0.5 font-medium text-slate-600">{t.language_name}</span>
            {t.text ?? "Translation pending (not wired up yet)"}
          </li>
        ))}
      </ul>

      {!msg.can_send && msg.blocked_reason && (
        <p className="mt-2 rounded-md bg-amber-50 px-2.5 py-1.5 text-[11px] text-amber-900">{msg.blocked_reason}</p>
      )}

      <div className="mt-3 flex items-center gap-2">
        <button
          onClick={onSend}
          disabled={!msg.can_send || send.kind === "sending"}
          className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40"
          title="Logs the message on the server; WhatsApp delivery is not connected yet"
        >
          {send.kind === "sending" ? "Sending…" : "Send (log only)"}
        </button>
        <button
          onClick={onCopy}
          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
        >
          {copied ? "Copied ✓" : "Copy text"}
        </button>
      </div>

      {send.kind === "logged" && (
        <p className="mt-2 text-[11px] text-slate-600">
          Logged on the server at {new Date(send.at).toLocaleTimeString("en-IN", { timeStyle: "short" })}. Not
          delivered: WhatsApp (Twilio) is not connected yet.
        </p>
      )}
      {send.kind === "error" && <p className="mt-2 text-[11px] text-red-700">{send.message}</p>}
    </Section>
  );
}

/** Render WhatsApp markup: *bold*, _italic_ and bare URLs. */
function formatWhatsApp(text: string): ReactNode[] {
  return text.split(/(\*[^*\n]+\*|_[^_\n]+_|https?:\/\/\S+)/g).map((part, i) => {
    if (/^\*[^*\n]+\*$/.test(part)) return <strong key={i}>{part.slice(1, -1)}</strong>;
    if (/^_[^_\n]+_$/.test(part)) return <em key={i}>{part.slice(1, -1)}</em>;
    if (/^https?:\/\//.test(part))
      return (
        <a key={i} href={part} target="_blank" rel="noreferrer" className="text-sky-700 underline">
          {part}
        </a>
      );
    return part;
  });
}
