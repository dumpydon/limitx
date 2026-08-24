"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { integer } from "@/lib/format";
import { Panel } from "./Panel";

interface ReplayData { position: number; total: number; snapshot: { checksum: string; live_order_count: number; sequence: number } | null; latest_entry: Record<string, unknown>[] | null }

export function ReplayLab({ symbol }: { symbol: string }) {
  const [data, setData] = useState<ReplayData | null>(null);
  const [position, setPosition] = useState(0);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (target?: number) => {
    setLoading(true);
    try {
      const query = target === undefined ? "" : `&position=${target}`;
      const result = await api<ReplayData>(`/api/replay/load?symbol=${symbol}${query}`, {
        method: "POST",
      });
      setData(result); setPosition(result.position);
    } finally { setLoading(false); }
  }, [symbol]);
  useEffect(() => { queueMicrotask(() => void load()); }, [load]);
  const latest = data?.latest_entry?.at(-1);
  return (
    <div className="view-stack">
      <Panel title="Deterministic Replay" eyebrow="COMMAND JOURNAL → IDENTICAL STATE" action={<button className="outline-button" onClick={() => void load()}>Reload live session</button>}>
        <div className="replay-hero"><div><span>COMMAND POSITION</span><strong>{integer(position)} <i>/ {integer(data?.total)}</i></strong></div><div><span>STATE CHECKSUM</span><strong className="checksum">{data?.snapshot?.checksum ?? "No state"}</strong></div><div><span>LIVE ORDERS</span><strong>{integer(data?.snapshot?.live_order_count)}</strong></div></div>
        <input className="timeline" type="range" min="0" max={data?.total ?? 0} value={Math.min(position, data?.total ?? 0)} onChange={(event) => setPosition(Number(event.target.value))} onPointerUp={() => void load(position)} aria-label="Replay sequence position" />
        <div className="replay-controls"><button onClick={() => void load(0)}>│◀</button><button onClick={() => void load(Math.max(0, position - 1))}>◀</button><button className="play" onClick={() => void load(Math.min(data?.total ?? 0, position + 1))}>▶</button><button onClick={() => void load(data?.total)}>▶│</button><span>{loading ? "Reconstructing…" : "Ready · replay uses command order, never wall time"}</span></div>
      </Panel>
      <div className="split-grid">
        <Panel title="Latest Event" eyebrow={`POSITION ${position}`}><pre className="event-detail">{latest ? JSON.stringify(latest, null, 2) : "No event at this position."}</pre></Panel>
        <Panel title="Recovery Pattern" eyebrow="SNAPSHOT + SUBSEQUENT EVENTS"><div className="flow-diagram"><div><b>01</b><span>Load canonical snapshot</span></div><i>→</i><div><b>02</b><span>Replay sequenced commands</span></div><i>→</i><div><b>03</b><span>Verify checksum</span></div></div><p className="prose">Jumping backward rebuilds from sequence zero in this lab. The snapshot store supports a faster warm start, followed by the same deterministic replay path.</p></Panel>
      </div>
    </div>
  );
}
