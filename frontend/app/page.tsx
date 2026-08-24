"use client";

import { useCallback, useEffect, useState } from "react";
import { DepthChart } from "@/components/DepthChart";
import { EngineView } from "@/components/EngineView";
import { LiveOrders } from "@/components/LiveOrders";
import { Metrics } from "@/components/Metrics";
import { OrderBook } from "@/components/OrderBook";
import { OrderEntry } from "@/components/OrderEntry";
import { PerformanceLab } from "@/components/PerformanceLab";
import { ReplayLab } from "@/components/ReplayLab";
import { Trades } from "@/components/Trades";
import { Panel } from "@/components/Panel";
import { api } from "@/lib/api";
import { price } from "@/lib/format";
import { useMarket } from "@/lib/useMarket";
import type { LiveOrder } from "@/types/market";

type View = "market" | "replay" | "performance" | "engine";

export default function Home() {
  const [symbol, setSymbol] = useState("BTC-USD"); const [view, setView] = useState<View>("market");
  const { market, trades, sequence, status, failureMode, setFailureMode } = useMarket(symbol);
  const [metrics, setMetrics] = useState<Record<string, number | null>>({}); const [system, setSystem] = useState<Record<string, number | string | null>>({}); const [orders, setOrders] = useState<LiveOrder[]>([]); const [events, setEvents] = useState<Record<string, unknown>[]>([]); const [scenario, setScenario] = useState("normal"); const [seed, setSeed] = useState(42); const [running, setRunning] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [metricData, systemData, orderData] = await Promise.all([
        api<{ metrics: Record<string, number | null> }>(`/api/metrics/${symbol}`), api<Record<string, number | string | null>>(`/api/system/${symbol}`), api<{ orders: LiveOrder[] }>(`/api/orders/live/${symbol}?account_id=demo-user`),
      ]);
      setMetrics(metricData.metrics); setSystem(systemData); setOrders(orderData.orders);
    } catch { /* connection state is already visible in the header */ }
  }, [symbol]);
  useEffect(() => { queueMicrotask(() => void refresh()); const timer = setInterval(() => void refresh(), 1200); return () => clearInterval(timer); }, [refresh]);

  function capture(newEvents: Record<string, unknown>[]) { setEvents((current) => [...newEvents.reverse(), ...current].slice(0, 80)); void refresh(); }
  async function cancel(order: LiveOrder) { const result = await api<{ events: Record<string, unknown>[] }>(`/api/orders/${order.order_id}?symbol=${symbol}&account_id=demo-user`, { method: "DELETE" }); capture(result.events); }
  async function start() { setRunning(true); await api("/api/simulation/start", { method: "POST", body: JSON.stringify({ symbol, scenario, seed, operations: 2500, speed: 5, reset: true }) }); }
  async function pause() { await api(`/api/simulation/${running ? "pause" : "resume"}?symbol=${symbol}`, { method: "POST" }); setRunning(!running); }
  async function reset() { await api(`/api/simulation/reset?symbol=${symbol}`, { method: "POST" }); setRunning(false); setEvents([]); await refresh(); }

  const mid = market.l1.mid_ticks_x2 === null ? null : market.l1.mid_ticks_x2 / 2;
  return <main className="app-shell">
    <header className="topbar"><div className="brand"><div className="brand-mark"><span>L</span><i>X</i></div><div><strong>LIMIT X</strong><span>MICROSTRUCTURE LAB</span></div></div><div className="symbol-control"><label htmlFor="symbol">INSTRUMENT</label><select id="symbol" value={symbol} onChange={(e) => setSymbol(e.target.value)}><option>BTC-USD</option><option>ETH-USD</option><option>AAPL</option><option>MSFT</option></select><div><strong>{price(mid)}</strong><span className="up">SIMULATED</span></div></div><div className="top-status"><div><span>ENGINE</span><strong className={status.toLowerCase()}><i />{status}</strong></div><div><span>SEQUENCE</span><strong className="mono">{sequence.toLocaleString()}</strong></div><div><span>CHECKSUM</span><strong className="mono checksum-short">{market.checksum}</strong></div></div></header>
    <nav className="nav-tabs" aria-label="Primary views">{(["market", "replay", "performance", "engine"] as View[]).map((item) => <button key={item} className={view === item ? "active" : ""} onClick={() => setView(item)}>{item === "market" ? "Market Lab" : item === "performance" ? "Performance" : item[0].toUpperCase() + item.slice(1)}</button>)}<span className="sim-disclaimer">SIMULATION ONLY · NO REAL TRADING</span></nav>
    {view === "market" ? <>
      <section className="control-strip"><div className="control-title"><span className="pulse-ring" /><div><strong>Market simulation</strong><span>{running ? "Deterministic order flow running" : "Ready to generate seeded order flow"}</span></div></div><label>Scenario<select value={scenario} onChange={(e) => setScenario(e.target.value)}><option value="normal">Normal market</option><option value="thin_liquidity">Thin liquidity</option><option value="high_volatility">High volatility</option><option value="cancel_storm">Cancel storm</option><option value="liquidity_shock">Liquidity shock</option><option value="large_market_sweep">Large sweep</option><option value="flash_selloff">Flash selloff</option></select></label><label>Seed<input type="number" value={seed} onChange={(e) => setSeed(Number(e.target.value))} /></label><label>Transport fault<select value={failureMode} onChange={(e) => setFailureMode(e.target.value as typeof failureMode)}><option value="none">None</option><option value="drop">Drop next delta</option><option value="delay">Delay next delta</option><option value="duplicate">Duplicate next delta</option></select></label><div className="sim-buttons"><button className="run-market" onClick={() => void start()}>▶ Run market</button><button onClick={() => void pause()}>{running ? "Ⅱ Pause" : "▶ Resume"}</button><button onClick={() => void reset()}>↺ Reset</button></div></section>
      <div className="market-grid"><OrderBook bids={market.depth.bids} asks={market.depth.asks} spread={market.l1.spread_ticks} /><DepthChart bids={market.depth.bids} asks={market.depth.asks} /><OrderEntry symbol={symbol} onResult={capture} /><Trades trades={trades} /><Metrics data={{ ...metrics, mid_ticks: mid }} /><LiveOrders orders={orders} onCancel={(order) => void cancel(order)} /><Panel title="Execution Events" eyebrow="STRUCTURED SEQUENCE"><div className="event-stream">{events.slice(0, 9).map((event, index) => <div key={`${String(event.sequence)}-${index}`}><span className="mono">{String(event.sequence ?? "—")}</span><b>{String(event.type ?? "EVENT").replaceAll("_", " ")}</b><i>{String(event.reason ?? event.order_id ?? "engine")}</i></div>)}{!events.length ? <div className="empty">Manual command events will appear here.</div> : null}</div></Panel></div>
    </> : null}
    {view === "replay" ? <ReplayLab symbol={symbol} /> : null}{view === "performance" ? <PerformanceLab /> : null}{view === "engine" ? <EngineView system={system} /> : null}
    <footer><span>Limit X / deterministic engine laboratory</span><span>Python matcher · FastAPI · Next.js</span><span>Fixed tick: $0.01</span></footer>
  </main>;
}
