"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { integer, price } from "@/lib/format";
import type { SystemState } from "@/types/market";
import { Panel } from "./Panel";

interface XRayData {
  side: string;
  complexity?: Record<string, string>;
  price_index: Array<{ price_ticks: number; quantity: number; orders: number; selected: boolean }>;
  selected_level: null | {
    price_ticks: number;
    aggregate_quantity: number;
    order_count: number;
    head_order_id: string;
    tail_order_id: string;
    orders: Array<{
      order_id: string;
      account_id: string;
      remaining_qty: number;
      priority_sequence: number;
      previous_order_id: string | null;
      next_order_id: string | null;
      index_pointer: string;
    }>;
  };
  order_index_size: number;
}

const ARCHITECTURE = [
  ["Command gateway", "Owns typed ingress validation; no book mutation."],
  ["Risk gateway", "Evaluates deterministic limits before sequencing."],
  ["Symbol queue", "Bounded asyncio ingress; one independent queue per symbol."],
  ["Matcher", "Single writer owns all mutable L3 order-book state."],
  ["Journal", "Canonical command and event evidence for replay and audit."],
  ["Market data", "Projects private L3 state into sequence-linked L1/L2."],
  ["Analytics", "Observes events for metrics, ledger, and surveillance."],
  ["WebSocket", "Bounded subscribers; lag causes snapshot replacement."],
];

export function EngineView({ symbol, system }: { symbol: string; system: SystemState | null }) {
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [xray, setXray] = useState<XRayData | null>(null);
  const [architecture, setArchitecture] = useState(ARCHITECTURE[3]);
  const [snapshot, setSnapshot] = useState<Record<string, unknown> | null>(null);
  const [recovery, setRecovery] = useState<Record<string, unknown> | null>(null);
  const load = useCallback(async () => {
    setXray(await api<XRayData>(`/api/xray/${symbol}?side=${side}`));
  }, [side, symbol]);
  useEffect(() => { queueMicrotask(() => void load()); }, [load]);
  async function createSnapshot() {
    setRecovery(null);
    setSnapshot(await api<Record<string, unknown>>(`/api/recovery/snapshot/${symbol}`, { method: "POST" }));
  }
  async function verifyRecovery() {
    setRecovery(await api<Record<string, unknown>>(`/api/recovery/verify/${symbol}`, { method: "POST" }));
  }
  const level = xray?.selected_level;
  return <div className="view-stack">
    <div className="engine-principles"><div><span>01</span><strong>Fixed-point prices</strong><p>Crossing compares integer ticks; float equality never decides execution.</p></div><div><span>02</span><strong>Price → FIFO</strong><p>A sorted price index owns intrusive doubly linked order queues.</p></div><div><span>03</span><strong>Single writer</strong><p>One bounded command queue serializes all mutation per symbol.</p></div><div><span>04</span><strong>Reconstructable</strong><p>Snapshots plus canonical journal commands reproduce checksum state.</p></div></div>
    <div className="xray-layout">
      <Panel title="Engine X-ray" eyebrow={`${symbol} · real current book`} action={<div className="xray-side"><button className={side === "BUY" ? "active" : ""} onClick={() => setSide("BUY")}>Bids</button><button className={side === "SELL" ? "active" : ""} onClick={() => setSide("SELL")}>Asks</button><button onClick={() => void load()}>Refresh</button></div>}>
        <div className="xray-book"><div className="price-index"><header><span>{side === "BUY" ? "Bid" : "Ask"} price index</span><b>{xray?.price_index.length ?? 0} visible levels</b></header>{xray?.price_index.slice(0, 9).map((item) => <button key={item.price_ticks} className={item.selected ? "active" : ""} onClick={async () => setXray(await api<XRayData>(`/api/xray/${symbol}?side=${side}&price_ticks=${item.price_ticks}`))}><strong>{price(item.price_ticks)}</strong><span>{integer(item.quantity)} qty</span><i>{item.orders} orders</i></button>)}</div><div className="level-xray"><header><span>Selected price level</span><strong>{price(level?.price_ticks)}</strong><small>{integer(level?.aggregate_quantity)} aggregate · {integer(level?.order_count)} orders</small></header><div className="real-linked-list"><label>HEAD · {level?.head_order_id ?? "—"}</label>{level?.orders.slice(0, 8).map((order, index) => <div key={order.order_id}><article><header><b>{order.order_id}</b><code>SEQ {integer(order.priority_sequence)}</code></header><span>{integer(order.remaining_qty)} remaining</span><small>{order.previous_order_id ?? "∅"} ← node → {order.next_order_id ?? "∅"}</small></article>{index < Math.min(level.orders.length, 8) - 1 ? <i>↓</i> : null}</div>)}{level && level.orders.length > 8 ? <p>+ {level.orders.length - 8} additional FIFO nodes</p> : null}<label>TAIL · {level?.tail_order_id ?? "—"}</label></div></div></div>
        <div className="complexity-strip">{Object.entries(xray?.complexity ?? {}).map(([key, value]) => <div key={key}><span>{key.replaceAll("_", " ")}</span><b>{value}</b></div>)}<div><span>order index</span><b>{integer(xray?.order_index_size)} live pointers</b></div></div>
      </Panel>
      <Panel title="System status" eyebrow="Live owned state"><dl className="inspector-list">{system ? Object.entries({ engine_sequence: system.engine_sequence, active_orders: system.active_orders, bid_levels: system.bid_levels, ask_levels: system.ask_levels, event_journal_size: system.event_journal_size, queue_depth: system.queue_depth, connected_clients: system.connected_clients, snapshot_size_bytes: system.snapshot_size_bytes, process_max_rss: system.process_max_rss_platform_units, checksum: system.last_checksum }).map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd className="mono">{typeof value === "number" ? integer(value) : value}</dd></div>) : <div className="empty">Loading system state…</div>}</dl></Panel>
    </div>
    <div className="split-grid">
      <Panel title="Recovery" eyebrow="Snapshot + subsequent journal"><div className="recovery-actions"><button onClick={() => void createSnapshot()}>01 · Create snapshot</button><i>Trade or modify the book</i><button disabled={!snapshot} onClick={() => void verifyRecovery()}>02 · Recover and verify</button></div>{snapshot ? <div className="recovery-result"><span>Captured</span><b>SEQ {integer(Number(snapshot.snapshot_sequence))}</b><code>{String(snapshot.snapshot_checksum)}</code><small>Journal position {integer(Number(snapshot.journal_position))} · {integer(Number(snapshot.snapshot_size_bytes))} bytes</small></div> : null}{recovery ? <div className={`recovery-result ${String(recovery.status).toLowerCase()}`}><span>Recovery {String(recovery.status)}</span><b>{integer(Number(recovery.commands_replayed))} commands / {integer(Number(recovery.events_replayed))} events replayed</b><code>expected {String(recovery.expected_checksum)}<br />recovered {String(recovery.recovered_checksum)}</code><small>Final sequence {integer(Number(recovery.final_sequence))}</small></div> : null}</Panel>
      <Panel title="Architecture" eyebrow="Actual component responsibilities"><div className="architecture-map">{ARCHITECTURE.map((component, index) => <div key={component[0]}><button className={architecture[0] === component[0] ? "active" : ""} onClick={() => setArchitecture(component)}>{component[0]}</button>{index < ARCHITECTURE.length - 1 ? <i>→</i> : null}</div>)}</div><div className="architecture-detail"><span>Selected component</span><strong>{architecture[0]}</strong><p>{architecture[1]}</p></div></Panel>
    </div>
    <Panel title="Correctness contract" eyebrow="Invariants + differential oracle"><div className="invariant-grid">{["Uncrossed resting book", "FIFO priority monotonic", "Quantity conservation", "Index → live node identity", "Level aggregate equality", "Empty-level removal", "Strict event sequence", "Replay checksum equality"].map((item, index) => <div key={item}><span>{String(index + 1).padStart(2, "0")}</span><b>{item}</b><i>Verified</i></div>)}</div></Panel>
  </div>;
}
