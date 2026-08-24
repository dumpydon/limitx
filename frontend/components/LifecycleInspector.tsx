"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { integer, price } from "@/lib/format";
import type { Lifecycle } from "@/types/market";

export function LifecycleInspector({
  symbol,
  orderId,
  onClose,
}: {
  symbol: string;
  orderId: string | null;
  onClose: () => void;
}) {
  const [data, setData] = useState<Lifecycle | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!orderId) return;
    queueMicrotask(() => {
      setData(null);
      setError(null);
      void api<Lifecycle>(`/api/orders/${symbol}/${orderId}/lifecycle`)
        .then(setData)
        .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Lifecycle unavailable"));
    });
  }, [orderId, symbol]);
  if (!orderId) return null;
  return (
    <div className="inspector-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="lifecycle-inspector" role="dialog" aria-modal="true" aria-label={`Order ${orderId} lifecycle`} onMouseDown={(event) => event.stopPropagation()}>
        <header><div><span>Order lifecycle · journal evidence</span><h2>{orderId}</h2></div><button aria-label="Close lifecycle inspector" onClick={onClose}>×</button></header>
        {error ? <div className="inspector-error">{error}</div> : null}
        {!data && !error ? <div className="inspector-loading">Reconstructing lifecycle from journal…</div> : null}
        {data ? <>
          <div className="lifecycle-summary"><div><span>Status</span><strong>{data.status.replaceAll("_", " ").toLowerCase()}</strong></div><div><span>Filled</span><strong>{integer(data.filled_quantity)} / {integer(data.requested_quantity)}</strong></div><div><span>Remaining</span><strong>{integer(data.remaining_quantity)}</strong></div><div><span>Trades</span><strong>{data.execution.trade_count}</strong></div></div>
          <div className="why-panel"><span>Why did this happen?</span><p>{data.explanation}</p></div>
          <div className="pipeline-evidence">{data.pipeline.map((stage, index) => <div key={`${stage.stage}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span><strong>{stage.stage}</strong><code>{stage.evidence_id}</code><small>{stage.basis}</small></div>)}</div>
          {data.execution.trade_count ? <div className="match-visualizer"><div className="match-input"><span>Incoming / resting order</span><strong>{integer(data.requested_quantity)} units</strong></div><i>↓</i><div className="match-fills">{data.execution.trades.map((trade, index) => <div key={`${String(trade.sequence)}-${index}`}><span>{integer(Number(trade.quantity))}</span><b>@ {price(Number(trade.price_ticks))}</b><small>SEQ {integer(Number(trade.sequence))}</small></div>)}</div><i>↓</i><div className="match-output"><span>VWAP</span><strong>{price(data.execution.vwap_ticks)}</strong><small>{data.execution.levels_consumed.length} levels consumed</small></div></div> : null}
          <div className="lifecycle-timeline">{data.timeline.map((event) => <article key={`${event.evidence_id}-${event.type}`}><div className="timeline-rail"><i /><span /></div><div><header><b>SEQ {integer(event.sequence)}</b><code>{event.evidence_id}</code></header><strong>{event.stage}</strong><small>{event.type.replaceAll("_", " ")}</small></div></article>)}</div>
        </> : null}
      </section>
    </div>
  );
}
