"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { CommandPalette } from "@/components/CommandPalette";
import { ControlsView } from "@/components/ControlsView";
import { DepthChart } from "@/components/DepthChart";
import { DotMatrixWordmark } from "@/components/DotMatrixWordmark";
import { EngineView } from "@/components/EngineView";
import { FailureLab } from "@/components/FailureLab";
import { LifecycleInspector } from "@/components/LifecycleInspector";
import { LiveOrders } from "@/components/LiveOrders";
import { LogoMark } from "@/components/LogoMark";
import { MarketOverview } from "@/components/MarketOverview";
import { Metrics } from "@/components/Metrics";
import { OrderBook } from "@/components/OrderBook";
import { OrderEntry } from "@/components/OrderEntry";
import { Panel } from "@/components/Panel";
import { PerformanceLab } from "@/components/PerformanceLab";
import { ReplayLab } from "@/components/ReplayLab";
import { Trades } from "@/components/Trades";
import { api } from "@/lib/api";
import { integer, price } from "@/lib/format";
import { useMarket } from "@/lib/useMarket";
import { useLogoPulse } from "@/lib/useLogoPulse";
import type { LogoPulse } from "@/types/logo";
import type { FailureMode, LiveOrder, MarketSummary, SystemState } from "@/types/market";

type View = "market" | "replay" | "performance" | "engine" | "controls";
interface SimulationState { status: string; scenario: string | null; seed: number | null; operations: number; speed: number }
interface ScenarioInfo { key: string; name: string; description: string; expected_characteristics: string }
interface RiskSummary { limits: { max_order_quantity: number; max_notional_ticks: number } }

const FALLBACK_REFERENCE: Record<string, number> = { "BTC-USD": 6_784_200, "ETH-USD": 384_200, AAPL: 23_475, MSFT: 41_885 };

export default function Home() {
  const [symbol, setSymbol] = useState("BTC-USD");
  const [view, setView] = useState<View>("market");
  const { market, trades, sequence, status, failureMode, setFailureMode, syncEvents, clearSyncEvents, enginePulse } = useMarket(symbol);
  const { pulse: logoPulse, trigger: triggerLogo } = useLogoPulse();
  const [logoPreview, setLogoPreview] = useState<"buy" | "sell" | null>(null);
  const [system, setSystem] = useState<SystemState | null>(null);
  const [orders, setOrders] = useState<LiveOrder[]>([]);
  const [events, setEvents] = useState<Record<string, unknown>[]>([]);
  const [markets, setMarkets] = useState<MarketSummary[]>([]);
  const [simulation, setSimulation] = useState<SimulationState>({ status: "IDLE", scenario: null, seed: 42, operations: 0, speed: 1 });
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  const [scenario, setScenario] = useState("normal");
  const [seed, setSeed] = useState(42);
  const [speed, setSpeed] = useState(1);
  const [risk, setRisk] = useState<RiskSummary | null>(null);
  const [inspectOrderId, setInspectOrderId] = useState<string | null>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [connectionError, setConnectionError] = useState(false);
  const autoStarted = useRef(new Set<string>());

  const refresh = useCallback(async () => {
    try {
      const [systemData, orderData, marketData, simulationData] = await Promise.all([
        api<SystemState>(`/api/system/${symbol}`),
        api<{ orders: LiveOrder[] }>(`/api/orders/live/${symbol}?account_id=demo-user`),
        api<{ markets: MarketSummary[] }>("/api/markets"),
        api<{ state: SimulationState }>(`/api/simulation/state/${symbol}`),
      ]);
      setSystem(systemData); setOrders(orderData.orders); setMarkets(marketData.markets); setSimulation(simulationData.state); setConnectionError(false);
      if (simulationData.state.status === "IDLE" && !autoStarted.current.has(symbol)) {
        autoStarted.current.add(symbol);
        void api("/api/simulation/start", { method: "POST", body: JSON.stringify({ symbol, scenario: "normal", seed: 42, operations: 50_000, speed: 1, reset: false }) });
      }
    } catch { setConnectionError(true); }
  }, [symbol]);

  useEffect(() => {
    queueMicrotask(() => void refresh());
    const timer = window.setInterval(() => void refresh(), 1500);
    return () => window.clearInterval(timer);
  }, [refresh]);
  useEffect(() => {
    queueMicrotask(() => {
      void Promise.all([
        api<{ scenarios: ScenarioInfo[] }>("/api/scenarios"),
        api<RiskSummary>("/api/risk"),
      ]).then(([scenarioData, riskData]) => { setScenarios(scenarioData.scenarios); setRisk(riskData); });
    });
  }, []);
  useEffect(() => {
    if (enginePulse) queueMicrotask(() => triggerLogo(enginePulse.type));
  }, [enginePulse, triggerLogo]);

  function capture(newEvents: Record<string, unknown>[], orderId?: string) {
    setEvents((current) => [[...newEvents].reverse(), current].flat().slice(0, 100));
    if (orderId) setInspectOrderId(orderId);
    const rejected = newEvents.some((event) => ["ORDER_REJECTED", "RISK_REJECTED", "CANCEL_REJECTED", "MODIFY_REJECTED"].includes(String(event.type)));
    const executions = newEvents.filter((event) => event.type === "TRADE_EXECUTED");
    const levels = new Set(executions.map((event) => Number(event.price_ticks)));
    const accepted = newEvents.find((event) => event.type === "ORDER_ACCEPTED");
    const semanticPulse: LogoPulse | null = rejected
      ? "reject"
      : levels.size >= 3
        ? "sweep"
        : executions.length
          ? "trade"
          : accepted
            ? accepted.side === "SELL" ? "sell" : "buy"
            : null;
    if (semanticPulse) triggerLogo(semanticPulse);
    void refresh();
  }
  async function cancel(order: LiveOrder) {
    const result = await api<{ events: Record<string, unknown>[] }>(`/api/orders/${order.order_id}?symbol=${symbol}&account_id=demo-user`, { method: "DELETE" });
    capture(result.events);
  }
  async function modify(order: LiveOrder) {
    const result = await api<{ events: Record<string, unknown>[] }>(`/api/orders/${order.order_id}`, { method: "PATCH", body: JSON.stringify({ symbol, account_id: "demo-user", new_quantity: Math.max(order.filled_qty + 1, order.quantity - 1), new_price_ticks: order.price_ticks }) });
    capture(result.events); setInspectOrderId(order.order_id);
  }
  const start = useCallback(async (selectedScenario = scenario) => {
    await api("/api/simulation/start", { method: "POST", body: JSON.stringify({ symbol, scenario: selectedScenario, seed, operations: 50_000, speed, reset: true }) });
    setScenario(selectedScenario); await refresh();
  }, [refresh, scenario, seed, speed, symbol]);
  const pause = useCallback(async () => {
    const action = simulation.status === "RUNNING" ? "pause" : "resume";
    await api(`/api/simulation/${action}?symbol=${symbol}`, { method: "POST" });
    await refresh();
  }, [refresh, simulation.status, symbol]);
  async function reset() {
    await api(`/api/simulation/reset?symbol=${symbol}`, { method: "POST" });
    setEvents([]); clearSyncEvents(); await refresh();
  }

  useEffect(() => {
    const shortcuts = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing = target?.matches("input, select, textarea, [contenteditable='true']");
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setPaletteOpen(true); return; }
      if (typing) return;
      if (event.key === " ") { event.preventDefault(); void pause(); }
      if (event.key.toLowerCase() === "r") setView("replay");
      if (event.key.toLowerCase() === "p") setView("performance");
      if (event.key.toLowerCase() === "e") setView("engine");
      if (event.key === "Escape") { setInspectOrderId(null); setPaletteOpen(false); }
    };
    window.addEventListener("keydown", shortcuts);
    return () => window.removeEventListener("keydown", shortcuts);
  }, [pause]);

  const mid = market.l1.mid_ticks_x2 === null ? null : market.l1.mid_ticks_x2 / 2;
  const last = system?.last_trade_ticks ?? mid;
  const currentScenario = scenarios.find((item) => item.key === scenario);
  const movementClass = (system?.absolute_move_ticks ?? 0) >= 0 ? "positive" : "negative";
  const statusLabel = connectionError ? "BACKEND UNAVAILABLE" : status === "RESYNCING" ? "RESYNCHRONIZING" : simulation.status;

  return <>
    <div className="footer-curtain-stage">
      <DotMatrixWordmark pulse={logoPulse} />
    </div>
    <main className="app-shell footer-curtain-content">
    <header className="topbar premium"><div className="brand"><LogoMark pulse={logoPulse} preview={logoPreview} /><small>Matching engine lab</small></div><div className="instrument-hero"><label>Simulated instrument</label><div><select value={symbol} onChange={(event) => setSymbol(event.target.value)} aria-label="Instrument"><option>BTC-USD</option><option>ETH-USD</option><option>AAPL</option><option>MSFT</option></select><strong>{price(last)}</strong><span className={movementClass}>{system ? `${system.absolute_move_ticks >= 0 ? "+" : ""}${price(system.absolute_move_ticks)} · ${system.percentage_move >= 0 ? "+" : ""}${system.percentage_move.toFixed(5)}%` : "—"}</span></div></div><div className="session-facts"><div><span>Simulated market</span><strong className={statusLabel.toLowerCase().replaceAll(" ", "-")}><i />{statusLabel}</strong></div><div><span>Sequence</span><strong className="mono sequence-value">{integer(sequence)}</strong></div><div><span>Seed / scenario</span><strong className="mono">{simulation.seed ?? seed} · {(simulation.scenario ?? scenario).replaceAll("_", " ")}</strong></div><button className="palette-trigger" aria-label="Open command palette" onClick={() => setPaletteOpen(true)}><span className="command-glyph">⌘</span><span className="command-word">Command</span><kbd>K</kbd></button></div></header>
    <nav className="nav-tabs" aria-label="Primary views">{(["market", "replay", "performance", "engine", "controls"] as View[]).map((item) => <button key={item} className={view === item ? "active" : ""} onClick={() => setView(item)}>{item === "market" ? "Market lab" : item === "performance" ? "Performance" : item === "engine" ? "Engine X-ray" : item === "controls" ? "Risk & surveillance" : "Replay"}</button>)}<span className="sim-disclaimer">Synthetic data · no real order routing</span></nav>
    <MarketOverview markets={markets} selected={symbol} onSelect={setSymbol} />
    {view === "market" ? <>
      <section className="control-strip"><div className="control-title"><span className="pulse-ring" /><div><strong>{simulation.status === "RUNNING" ? "Deterministic market running" : `Market ${simulation.status.toLowerCase()}`}</strong><span>{currentScenario?.description ?? "Seeded synthetic order flow through the real matcher."}</span></div></div><label>Scenario<select value={scenario} onChange={(event) => setScenario(event.target.value)}>{scenarios.map((item) => <option value={item.key} key={item.key}>{item.name}</option>)}</select></label><label>Seed<input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value))} /></label><label>Speed<select value={speed} onChange={(event) => setSpeed(Number(event.target.value))}><option value="0.25">0.25×</option><option value="0.5">0.5×</option><option value="1">1×</option><option value="2">2×</option><option value="5">5×</option><option value="50">Max</option></select></label><div className="sim-buttons"><button className="run-market" onClick={() => void start()}>▶ Run scenario</button><button onClick={() => void pause()}>{simulation.status === "RUNNING" ? "Ⅱ Pause" : "▶ Resume"}</button><button onClick={() => void reset()}>↺ Reset</button></div><footer>{currentScenario?.expected_characteristics}</footer></section>
      <div className="market-grid"><OrderBook bids={market.depth.bids} asks={market.depth.asks} spread={market.l1.spread_ticks} mid={mid} /><DepthChart bids={market.depth.bids} asks={market.depth.asks} /><OrderEntry key={`${symbol}-${system?.reference_price_ticks}`} symbol={symbol} referencePriceTicks={system?.reference_price_ticks ?? FALLBACK_REFERENCE[symbol]} riskLimits={risk?.limits} onResult={capture} onInspect={setInspectOrderId} onSidePreview={setLogoPreview} /><Trades trades={trades} /><Metrics data={{ ...(system?.metrics ?? {}), mid_ticks: mid }} /><LiveOrders orders={orders} onCancel={(order) => void cancel(order)} onModify={(order) => void modify(order)} onInspect={setInspectOrderId} /><Panel title="Execution events" eyebrow="Manual command reports"><div className="event-stream">{events.slice(0, 10).map((event, index) => <button key={`${String(event.sequence)}-${index}`} onClick={() => event.order_id && setInspectOrderId(String(event.order_id))}><span className="mono">{String(event.sequence ?? "—")}</span><b>{String(event.type ?? "Event").replaceAll("_", " ")}</b><i>{String(event.reason ?? event.order_id ?? "engine")}</i></button>)}{!events.length ? <div className="empty">Submit an order to inspect its sequenced execution report.</div> : null}</div></Panel><FailureLab mode={failureMode} onMode={(mode: FailureMode) => setFailureMode(mode)} events={syncEvents} engineChecksum={system?.last_checksum ?? market.checksum} onClear={clearSyncEvents} /></div>
    </> : null}
    {view === "replay" ? <ReplayLab symbol={symbol} /> : null}
    {view === "performance" ? <PerformanceLab /> : null}
    {view === "engine" ? <EngineView symbol={symbol} system={system} /> : null}
    {view === "controls" ? <ControlsView symbol={symbol} /> : null}
    <footer className="app-footer"><span>Limit X / matching-engine observatory</span><span>Python matcher · single writer · sequence-linked market data</span><span>Simulation only</span></footer>
    </main>
    <div className="footer-curtain-spacer" aria-hidden="true" />
    <LifecycleInspector symbol={symbol} orderId={inspectOrderId} onClose={() => setInspectOrderId(null)} />
    <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} commands={[
      { label: "Run normal market", hint: "seeded deterministic session", run: () => void start("normal") },
      { label: "Run cancel storm", hint: "stress arbitrary unlink path", run: () => void start("cancel_storm") },
      { label: "Run large buy sweep", hint: "consume multiple ask levels", run: () => void start("large_buy_sweep") },
      { label: simulation.status === "RUNNING" ? "Pause simulation" : "Resume simulation", hint: "Space", run: () => void pause() },
      { label: "Open replay", hint: "R", run: () => setView("replay") },
      { label: "Open Engine X-Ray", hint: "E", run: () => setView("engine") },
      { label: "Open Performance Lab", hint: "P", run: () => setView("performance") },
      { label: "Switch BTC-USD", hint: "independent symbol worker", run: () => setSymbol("BTC-USD") },
      { label: "Switch ETH-USD", hint: "independent symbol worker", run: () => setSymbol("ETH-USD") },
    ]} />
  </>;
}
