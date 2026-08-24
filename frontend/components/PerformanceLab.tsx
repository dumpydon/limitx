"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { integer, latency } from "@/lib/format";
import { Panel } from "./Panel";

interface Result { scenario: string; operations: number; seed: number; throughput_ops_per_second: number; p50_ns: number; p95_ns: number; p99_ns: number; max_ns: number; elapsed_seconds: number; trades: number; cancels: number; modifies: number; python_version: string; platform: string; warmup_operations: number }

export function PerformanceLab() {
  const [scenario, setScenario] = useState("mixed"); const [operations, setOperations] = useState(10_000); const [seed, setSeed] = useState(42); const [result, setResult] = useState<Result | null>(null); const [running, setRunning] = useState(false);
  async function run() { setRunning(true); try { setResult(await api<Result>("/api/benchmarks", { method: "POST", body: JSON.stringify({ scenario, operations, seed, runs: 1 }) })); } finally { setRunning(false); } }
  const values = result ? [result.p50_ns, result.p95_ns, result.p99_ns, result.max_ns] : [];
  const max = Math.max(...values, 1);
  return <div className="view-stack">
    <Panel title="Core Engine Benchmark" eyebrow="DIRECT CALLS · HTTP AND UI EXCLUDED" action={<span className="truth-badge">Measured locally</span>}>
      <div className="benchmark-controls"><label>Scenario<select value={scenario} onChange={(e) => setScenario(e.target.value)}><option value="mixed">Mixed flow</option><option value="cancel_storm">Cancel storm</option><option value="sweep">Large sweeps</option></select></label><label>Operations<select value={operations} onChange={(e) => setOperations(Number(e.target.value))}><option value="10000">10,000</option><option value="50000">50,000</option><option value="100000">100,000</option></select></label><label>Seed<input type="number" value={seed} onChange={(e) => setSeed(Number(e.target.value))} /></label><button className="run-benchmark" disabled={running} onClick={() => void run()}>{running ? "Measuring…" : "Run benchmark"}</button></div>
    </Panel>
    <div className="benchmark-kpis">{[["THROUGHPUT", result ? `${integer(result.throughput_ops_per_second)} ops/s` : "Not measured"], ["P50 LATENCY", latency(result?.p50_ns)], ["P95 LATENCY", latency(result?.p95_ns)], ["P99 LATENCY", latency(result?.p99_ns)]].map(([label,value]) => <div className="kpi" key={label}><span>{label}</span><strong>{value}</strong><i>{result ? `seed ${result.seed}` : "run required"}</i></div>)}</div>
    <div className="split-grid"><Panel title="Latency Distribution" eyebrow="PER-OPERATION PERF_COUNTER_NS"><div className="latency-chart">{["p50", "p95", "p99", "max"].map((label,index) => <div key={label}><span>{label}</span><i style={{ height: result ? `${Math.max(4, (values[index] / max) * 180)}px` : "2px" }} /><strong>{latency(values[index])}</strong></div>)}</div></Panel><Panel title="Methodology" eyebrow="NO DECORATIVE TELEMETRY"><dl className="method-list"><div><dt>Warm-up</dt><dd>{result ? integer(result.warmup_operations) : "—"}</dd></div><div><dt>Workload</dt><dd>{result?.scenario ?? "—"}</dd></div><div><dt>Trades</dt><dd>{integer(result?.trades)}</dd></div><div><dt>Cancels / modifies</dt><dd>{result ? `${integer(result.cancels)} / ${integer(result.modifies)}` : "—"}</dd></div><div><dt>Runtime</dt><dd>{result ? `Python ${result.python_version}` : "—"}</dd></div></dl><p className="prose">These are noisy local CPython observations, not production latency guarantees. Timer overhead is included in each per-operation sample.</p></Panel></div>
  </div>;
}

