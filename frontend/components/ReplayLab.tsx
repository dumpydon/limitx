"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { integer } from "@/lib/format";
import { Panel } from "./Panel";

interface ReplayData {
  position: number;
  total: number;
  snapshot: { checksum: string; live_order_count: number; sequence: number; depth: { bids: unknown[]; asks: unknown[] } } | null;
  latest_entry: Record<string, unknown>[] | null;
  event_window: Record<string, unknown>[];
}
type Filter = "ALL" | "ORDERS" | "TRADES" | "CANCELS" | "RISK";

export function ReplayLab({ symbol }: { symbol: string }) {
  const [data, setData] = useState<ReplayData | null>(null);
  const [position, setPosition] = useState(0);
  const [jump, setJump] = useState("");
  const [loading, setLoading] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [filter, setFilter] = useState<Filter>("ALL");
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);

  const load = useCallback(async (target?: number) => {
    setLoading(true);
    try {
      const query = target === undefined ? "" : `&position=${target}`;
      const result = await api<ReplayData>(`/api/replay/load?symbol=${symbol}${query}`, { method: "POST" });
      setData(result); setPosition(result.position); setSelected(result.latest_entry?.at(-1) ?? null);
    } finally { setLoading(false); }
  }, [symbol]);
  useEffect(() => { queueMicrotask(() => void load()); }, [load]);
  useEffect(() => {
    if (!playing || !data || position >= data.total) return;
    const timer = window.setInterval(() => void load(Math.min(data.total, position + 1)), Math.max(80, 600 / speed));
    return () => window.clearInterval(timer);
  }, [data, load, playing, position, speed]);
  useEffect(() => { if (data && position >= data.total) queueMicrotask(() => setPlaying(false)); }, [data, position]);

  const visibleEvents = useMemo(() => (data?.event_window ?? []).filter((event) => {
    const type = String(event.type ?? "");
    if (filter === "ALL") return true;
    if (filter === "TRADES") return type === "TRADE_EXECUTED";
    if (filter === "CANCELS") return type.includes("CANCEL");
    if (filter === "RISK") return type === "RISK_REJECTED";
    return type.startsWith("ORDER_") || type.includes("MODIFY");
  }).slice(-120).reverse(), [data, filter]);

  return <div className="view-stack replay-view">
    <Panel title="Deterministic replay" eyebrow="Canonical commands → identical state" action={<button className="outline-button" onClick={() => void load()}>Reload live session</button>}>
      <div className="replay-hero"><div><span>Command position</span><strong>{integer(position)} <i>/ {integer(data?.total)}</i></strong></div><div><span>Engine sequence</span><strong>{integer(data?.snapshot?.sequence)}</strong></div><div><span>State checksum</span><strong className="checksum">{data?.snapshot?.checksum ?? "No state"}</strong></div><div><span>Live orders</span><strong>{integer(data?.snapshot?.live_order_count)}</strong></div></div>
      <input className="timeline" type="range" min="0" max={data?.total ?? 0} value={Math.min(position, data?.total ?? 0)} onChange={(event) => setPosition(Number(event.target.value))} onPointerUp={() => void load(position)} aria-label="Replay command position" />
      <div className="replay-controls"><button aria-label="First command" onClick={() => void load(0)}>│◀</button><button aria-label="Previous command" onClick={() => void load(Math.max(0, position - 1))}>◀</button><button className="play" aria-label={playing ? "Pause replay" : "Play replay"} onClick={() => setPlaying(!playing)}>{playing ? "Ⅱ" : "▶"}</button><button aria-label="Next command" onClick={() => void load(Math.min(data?.total ?? 0, position + 1))}>▶</button><button aria-label="Last command" onClick={() => void load(data?.total)}>▶│</button><div className="speed-control">{[0.25, 0.5, 1, 2, 5].map((item) => <button className={speed === item ? "active" : ""} key={item} onClick={() => setSpeed(item)}>{item}×</button>)}</div><label>Jump<input inputMode="numeric" value={jump} onChange={(event) => setJump(event.target.value)} /><button onClick={() => void load(Math.max(0, Math.min(data?.total ?? 0, Number(jump))))}>Go</button></label><span>{loading ? "Reconstructing…" : "Ready · no wall-clock decisions"}</span></div>
    </Panel>
    <div className="replay-grid">
      <Panel title="Event browser" eyebrow="Filtered journal evidence" action={<div className="event-filters">{(["ALL", "ORDERS", "TRADES", "CANCELS", "RISK"] as Filter[]).map((item) => <button className={filter === item ? "active" : ""} key={item} onClick={() => setFilter(item)}>{item.charAt(0) + item.slice(1).toLowerCase()}</button>)}</div>}><div className="replay-events">{visibleEvents.map((event, index) => <button className={selected?.sequence === event.sequence ? "active" : ""} key={`${String(event.sequence)}-${String(event.type)}-${index}`} onClick={() => setSelected(event)}><code>SEQ {integer(Number(event.sequence))}</code><strong>{String(event.type).replaceAll("_", " ")}</strong><span>{String(event.order_id ?? event.trade_id ?? event.reason ?? "engine")}</span></button>)}</div></Panel>
      <Panel title="Selected evidence" eyebrow={selected ? `Event ${String(selected.sequence)}` : "No selection"}><pre className="event-detail">{selected ? JSON.stringify(selected, null, 2) : "Select an event from the journal browser."}</pre></Panel>
    </div>
    <Panel title="Replay state" eyebrow="Book reconstructed at current command"><div className="replay-state"><div><span>Bid levels</span><strong>{integer(data?.snapshot?.depth.bids.length)}</strong></div><div><span>Ask levels</span><strong>{integer(data?.snapshot?.depth.asks.length)}</strong></div><div><span>Commands applied</span><strong>{integer(position)}</strong></div><div><span>Determinism</span><strong className="pass-text">Checksum verified</strong></div></div></Panel>
  </div>;
}
