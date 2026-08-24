"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { integer, latency, price } from "@/lib/format";
import { Panel } from "./Panel";

interface RiskData {
  limits: { max_order_quantity: number; max_notional_ticks: number; max_live_orders: number; max_position: number; price_collar_bps: number };
  rejection_counts: Record<string, number>;
  recent_rejections: Array<Record<string, unknown>>;
}
interface Comparison { caution: string; left: Record<string, number | string | null>; right: Record<string, number | string | null> }
interface Analysis { summary: string; claims: Array<{ claim: string; evidence_ids: string[] }>; disclaimer: string }

function experimentValue(key: string, value: number | string | null): string {
  const numeric = Number(value);
  if (value === null || Number.isNaN(numeric)) return "—";
  if (key === "vwap_ticks") return price(numeric);
  if (key === "p99_operation_ns") return latency(numeric);
  if (["cancel_add_ratio", "fill_ratio"].includes(key)) return numeric.toFixed(3);
  if (["average_spread_ticks", "median_spread_ticks", "price_impact_ticks"].includes(key)) return `${numeric.toFixed(2)} ticks`;
  return integer(numeric);
}

export function ControlsView({ symbol }: { symbol: string }) {
  const [risk, setRisk] = useState<RiskData | null>(null);
  const [alerts, setAlerts] = useState<Array<Record<string, unknown>>>([]);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [question, setQuestion] = useState("What caused the largest move?");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    const [riskData, metricData] = await Promise.all([
      api<RiskData>("/api/risk"),
      api<{ surveillance_alerts: Array<Record<string, unknown>> }>(`/api/metrics/${symbol}`),
    ]);
    setRisk(riskData); setAlerts(metricData.surveillance_alerts);
  }, [symbol]);
  useEffect(() => { queueMicrotask(() => void load()); }, [load]);
  async function saveRisk() {
    if (!risk) return;
    setRisk(await api<RiskData>("/api/risk", { method: "POST", body: JSON.stringify(risk.limits) }));
  }
  async function compare() {
    setBusy(true); try { setComparison(await api<Comparison>("/api/experiments/compare", { method: "POST", body: JSON.stringify({ left: "normal", right: "thin_liquidity", symbol, seed: 42, operations: 1000 }) })); } finally { setBusy(false); }
  }
  async function analyze() {
    setAnalysis(await api<Analysis>("/api/analyst", { method: "POST", body: JSON.stringify({ symbol, question }) }));
  }
  return <div className="view-stack controls-view">
    <div className="split-grid">
      <Panel title="Risk controls" eyebrow="Deterministic pre-trade gate" action={<button className="outline-button" onClick={() => void saveRisk()}>Apply safe limits</button>}>
        {risk ? <div className="risk-grid">{(["max_order_quantity", "max_notional_ticks", "max_live_orders", "max_position", "price_collar_bps"] as const).map((key) => <label key={key}>{key.replaceAll("_", " ")}<input type="number" value={risk.limits[key]} onChange={(event) => setRisk({ ...risk, limits: { ...risk.limits, [key]: Number(event.target.value) } })} /></label>)}</div> : <div className="empty">Loading risk configuration…</div>}
        <div className="rejection-counters">{Object.entries(risk?.rejection_counts ?? {}).map(([rule, count]) => <div key={rule}><span>{rule}</span><b>{count}</b></div>)}{!Object.keys(risk?.rejection_counts ?? {}).length ? <p>No risk rejections in current sessions.</p> : null}</div>
        {risk?.recent_rejections[0] ? <div className="risk-evidence"><span>Latest rejection</span><strong>{String(risk.recent_rejections[0].reason)}</strong><code>observed {String(risk.recent_rejections[0].observed)} · threshold {String(risk.recent_rejections[0].threshold)}</code></div> : null}
      </Panel>
      <Panel title="Surveillance" eyebrow="Heuristic signals · not proof of misconduct" action={<span className="tag">{alerts.length} alerts</span>}>
        <div className="alert-list">{alerts.map((alert) => <article key={String(alert.alert_id)}><header><b>{String(alert.rule).replaceAll("_", " ")}</b><span>{String(alert.participant)}</span></header><p>{String(alert.explanation)}</p><footer>{(alert.evidence_ids as string[]).map((id) => <code key={id}>{id}</code>)}</footer></article>)}{!alerts.length ? <div className="empty">No heuristic surveillance signal currently meets a rule threshold.</div> : null}</div>
      </Panel>
    </div>
    <Panel title="Compare scenarios" eyebrow="Same seed · independent deterministic runs" action={<button className="run-benchmark" disabled={busy} onClick={() => void compare()}>{busy ? "Running…" : "Compare normal vs thin"}</button>}>
      {comparison ? <><div className="comparison-table"><span>Metric</span><b>Normal</b><b>Thin liquidity</b>{[["Average spread", "average_spread_ticks"], ["Median spread", "median_spread_ticks"], ["Trades", "trade_count"], ["Volume", "volume"], ["VWAP", "vwap_ticks"], ["Price impact", "price_impact_ticks"], ["Cancel/add", "cancel_add_ratio"], ["Fill ratio", "fill_ratio"], ["p99 op", "p99_operation_ns"]].map(([label, key]) => <div key={key} className="comparison-row"><span>{label}</span><strong>{experimentValue(key, comparison.left[key])}</strong><strong>{experimentValue(key, comparison.right[key])}</strong></div>)}</div><p className="prose">{comparison.caution}</p></> : <div className="empty compact-empty">Run a controlled experiment to compare actual engine outputs.</div>}
    </Panel>
    <Panel title="Replay analyst" eyebrow="Read-only · evidence-grounded fallback"><div className="analyst-controls"><input value={question} onChange={(event) => setQuestion(event.target.value)} aria-label="Replay Analyst question" /><button onClick={() => void analyze()}>Analyze evidence</button></div>{analysis ? <div className="analysis-output"><p>{analysis.summary}</p>{analysis.claims.map((claim, index) => <article key={`${claim.claim}-${index}`}><strong>{claim.claim}</strong><div>{claim.evidence_ids.map((id) => <code key={id}>{id}</code>)}</div></article>)}<small>{analysis.disclaimer}</small></div> : null}</Panel>
  </div>;
}
