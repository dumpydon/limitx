"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { integer, latency } from "@/lib/format";
import { Panel } from "./Panel";

interface Result {
  scenario: string;
  operations: number;
  seed: number;
  runs: number;
  symbol_count: number;
  throughput_ops_per_second: number;
  p50_ns: number;
  p95_ns: number;
  p99_ns: number;
  max_ns: number;
  elapsed_seconds: number;
  trades: number;
  adds: number;
  cancels: number;
  modifies: number;
  active_orders: number;
  price_levels: number;
  max_rss_platform_units: number;
  python_version: string;
  platform: string;
  warmup_operations: number;
  latency_histogram: Array<{ range: string; count: number }>;
}

export function PerformanceLab() {
  const [scenario, setScenario] = useState("mixed");
  const [operations, setOperations] = useState(10_000);
  const [seed, setSeed] = useState(42);
  const [symbolCount, setSymbolCount] = useState(1);
  const [mix, setMix] = useState({ add: 66, cancel: 22, modify: 12 });
  const [result, setResult] = useState<Result | null>(null);
  const [history, setHistory] = useState<Result[]>([]);
  const [running, setRunning] = useState(false);
  useEffect(() => { queueMicrotask(() => void api<{ runs: Result[] }>("/api/benchmarks/history").then((data) => setHistory(data.runs))); }, []);
  async function run() {
    setRunning(true);
    try {
      const next = await api<Result>("/api/benchmarks", { method: "POST", body: JSON.stringify({ scenario, operations, seed, runs: 1, symbol_count: symbolCount, add_percent: mix.add, cancel_percent: mix.cancel, modify_percent: mix.modify }) });
      setResult(next);
      setHistory((current) => [next, ...current].slice(0, 20));
    } finally { setRunning(false); }
  }
  const previous = history.find((item) => item !== result && item.scenario === result?.scenario);
  const maxBucket = Math.max(1, ...(result?.latency_histogram.map((item) => item.count) ?? []));
  const throughputDelta = result && previous ? ((result.throughput_ops_per_second / previous.throughput_ops_per_second) - 1) * 100 : null;
  const p99Delta = result && previous ? ((result.p99_ns / previous.p99_ns) - 1) * 100 : null;
  const memoryDelta = result && previous ? result.max_rss_platform_units - previous.max_rss_platform_units : null;
  return <div className="view-stack performance-view">
    <Panel title="Engine performance" eyebrow="Direct matcher calls · HTTP and UI excluded" action={<span className="truth-badge">Measured, never decorative</span>}>
      <div className="benchmark-controls advanced"><label>Workload<select value={scenario} onChange={(event) => setScenario(event.target.value)}><option value="mixed">Mixed flow</option><option value="cancel_storm">Cancel storm</option><option value="sweep">Large sweeps</option></select></label><label>Operations<select value={operations} onChange={(event) => setOperations(Number(event.target.value))}><option value="10000">10,000</option><option value="50000">50,000</option><option value="100000">100,000</option><option value="1000000">1,000,000 · memory stress</option></select></label><label>Seed<input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value))} /></label><label>Symbols<select value={symbolCount} onChange={(event) => setSymbolCount(Number(event.target.value))}><option value="1">1 symbol</option><option value="2">2 symbols</option><option value="4">4 symbols</option></select></label><button className="run-benchmark" disabled={running || mix.add + mix.cancel + mix.modify !== 100} onClick={() => void run()}>{running ? "Measuring core…" : "Run benchmark"}</button></div>
      <div className="mix-controls">{(["add", "cancel", "modify"] as const).map((key) => <label key={key}>{key.charAt(0).toUpperCase() + key.slice(1)} %<input type="number" min="0" max="100" value={mix[key]} onChange={(event) => setMix({ ...mix, [key]: Number(event.target.value) })} /></label>)}<span className={mix.add + mix.cancel + mix.modify === 100 ? "valid" : "invalid"}>Total {mix.add + mix.cancel + mix.modify}%</span></div>
    </Panel>
    <div className="benchmark-kpis six">{[["Total ops", integer(result?.operations)], ["Elapsed", result ? `${result.elapsed_seconds.toFixed(3)} s` : "Not measured"], ["Throughput", result ? `${integer(result.throughput_ops_per_second)} ops/s` : "Not measured"], ["P50", latency(result?.p50_ns)], ["P99", latency(result?.p99_ns)], ["Max", latency(result?.max_ns)]].map(([label, value]) => <div className="kpi" key={label}><span>{label}</span><strong>{value}</strong><i>{result ? `${result.scenario} · seed ${result.seed}` : "run required"}</i></div>)}</div>
    <div className="split-grid performance-split"><Panel title="Latency distribution" eyebrow="Per-operation perf_counter_ns"><div className="histogram">{(result?.latency_histogram ?? []).map((bucket) => <div key={bucket.range}><i style={{ height: `${Math.max(2, (bucket.count / maxBucket) * 190)}px` }} /><strong>{integer(bucket.count)}</strong><span>{bucket.range} ns</span></div>)}{!result ? <div className="empty">Run a benchmark to populate measured buckets.</div> : null}</div></Panel><Panel title="Run details" eyebrow="Environment and resulting engine state"><dl className="method-list">{[["Warm-up", integer(result?.warmup_operations)], ["Python", result?.python_version ?? "—"], ["Symbols", integer(result?.symbol_count)], ["Adds / cancels / modifies", result ? `${integer(result.adds)} / ${integer(result.cancels)} / ${integer(result.modifies)}` : "—"], ["Trades", integer(result?.trades)], ["Active orders", integer(result?.active_orders)], ["Price levels", integer(result?.price_levels)], ["RSS platform units", integer(result?.max_rss_platform_units)]].map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl><p className="prose">Timer overhead, allocation, event retention, GC, scheduler state, and CPU power state affect these local CPython distributions.</p></Panel></div>
    <Panel title="Performance history" eyebrow="Local run comparison · no significance claim"><div className="history-grid"><div className="history-summary"><span>Run A → Run B</span><strong>{throughputDelta === null ? "Run twice to compare" : `${throughputDelta >= 0 ? "+" : ""}${throughputDelta.toFixed(1)}% throughput`}</strong><b>{p99Delta === null ? "—" : `${p99Delta >= 0 ? "+" : ""}${p99Delta.toFixed(1)}% p99`}</b><b>{memoryDelta === null ? "—" : `${memoryDelta >= 0 ? "+" : ""}${integer(memoryDelta)} RSS units`}</b><small>One noisy run is descriptive, not statistically significant.</small></div><div className="history-table"><header><span>Workload</span><span>Ops/s</span><span>p99</span><span>Symbols</span></header>{history.slice(0, 8).map((item, index) => <div key={`${item.seed}-${item.operations}-${index}`}><span>{item.scenario} / {integer(item.operations)}</span><b>{integer(item.throughput_ops_per_second)}</b><code>{latency(item.p99_ns)}</code><span>{item.symbol_count}</span></div>)}</div></div></Panel>
  </div>;
}
