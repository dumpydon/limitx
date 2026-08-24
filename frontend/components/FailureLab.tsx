"use client";

import type { FailureMode, SyncEvent } from "@/types/market";
import { Panel } from "./Panel";

export function FailureLab({
  mode,
  onMode,
  events,
  engineChecksum,
  onClear,
}: {
  mode: FailureMode;
  onMode: (mode: FailureMode) => void;
  events: SyncEvent[];
  engineChecksum: string;
  onClear: () => void;
}) {
  return (
    <Panel title="Failure lab" eyebrow="Transport faults · matcher untouched" action={<button className="text-button" onClick={onClear}>Clear log</button>}>
      <div className="fault-buttons">{([
        ["drop", "Drop next delta"],
        ["duplicate", "Duplicate next delta"],
        ["delay", "Delay next delta"],
        ["out_of_order", "Out-of-order delivery"],
      ] as Array<[FailureMode, string]>).map(([value, label]) => <button key={value} className={mode === value ? "active" : ""} onClick={() => onMode(mode === value ? "none" : value)}>{label}</button>)}</div>
      <div className="recovery-log">{events.map((event) => <div key={event.id} className={event.state.toLowerCase()}><span>{event.state}</span><p>{event.detail}</p>{event.expected !== undefined ? <code>EXPECTED {event.expected} · RECEIVED {event.received ?? "—"}</code> : null}</div>)}{!events.length ? <div className="empty compact-empty">Arm a fault, then run the market. Only the client delivery path is altered.</div> : null}</div>
      <footer className="fault-footer"><span>Engine checksum</span><code>{engineChecksum}</code><b>Core state remains authoritative</b></footer>
    </Panel>
  );
}
