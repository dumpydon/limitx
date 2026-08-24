"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { decimalToTicks } from "@/lib/format";
import type { Side } from "@/types/market";
import { Panel } from "./Panel";

export function OrderEntry({ symbol, onResult }: { symbol: string; onResult: (events: Record<string, unknown>[]) => void }) {
  const [side, setSide] = useState<Side>("BUY");
  const [type, setType] = useState<"LIMIT" | "MARKET">("LIMIT");
  const [tif, setTif] = useState("GTC");
  const [quantity, setQuantity] = useState("25");
  const [orderPrice, setOrderPrice] = useState("99999.95");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Ready for simulated order");

  async function submit() {
    const ticks = type === "LIMIT" ? decimalToTicks(orderPrice) : null;
    if (type === "LIMIT" && ticks === null) {
      setMessage("Enter a valid price with at most 2 decimals");
      return;
    }
    setBusy(true);
    try {
      const result = await api<{ events: Record<string, unknown>[] }>("/api/orders", {
        method: "POST",
        body: JSON.stringify({
          order_id: `UI-${Date.now()}-${Math.floor(Math.random() * 10_000)}`,
          symbol,
          account_id: "demo-user",
          side,
          order_type: type,
          time_in_force: tif,
          quantity: Number.parseInt(quantity, 10),
          price_ticks: ticks,
        }),
      });
      onResult(result.events);
      const precedence = [
        "ORDER_REJECTED",
        "RISK_REJECTED",
        "ORDER_FILLED",
        "ORDER_PARTIALLY_FILLED",
        "ORDER_CANCELLED",
        "ORDER_ACCEPTED",
      ];
      const decisiveType = precedence.find((candidate) =>
        result.events.some((event) => event.type === candidate),
      );
      const decisive = result.events.find((event) => event.type === decisiveType);
      setMessage(String(decisive?.type ?? "PROCESSED").replaceAll("_", " "));
    } catch (error) {
      setMessage(error instanceof Error ? error.message.slice(0, 90) : "Order failed");
    } finally {
      setBusy(false);
    }
  }

  const tifs = type === "MARKET" ? ["IOC", "FOK"] : ["GTC", "IOC", "FOK", "POST_ONLY"];
  return (
    <Panel title="Order Entry" eyebrow="SIMULATED · NO REAL ROUTING" className="entry-panel">
      <div className="segmented side-selector">
        <button className={side === "BUY" ? "active buy" : ""} onClick={() => setSide("BUY")}>Buy</button>
        <button className={side === "SELL" ? "active sell" : ""} onClick={() => setSide("SELL")}>Sell</button>
      </div>
      <label>Order type<select value={type} onChange={(event) => { const nextType = event.target.value as "LIMIT" | "MARKET"; setType(nextType); if (nextType === "MARKET" && !["IOC", "FOK"].includes(tif)) setTif("IOC"); }}><option>LIMIT</option><option>MARKET</option></select></label>
      <label>Quantity<input inputMode="numeric" value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label>
      <label>Price <span>USD · 0.01 tick</span><input disabled={type === "MARKET"} inputMode="decimal" value={orderPrice} onChange={(event) => setOrderPrice(event.target.value)} /></label>
      <label>Time in force<select value={tif} onChange={(event) => setTif(event.target.value)}>{tifs.map((item) => <option key={item}>{item}</option>)}</select></label>
      <button className={`submit-order ${side.toLowerCase()}`} disabled={busy} onClick={() => void submit()}>{busy ? "Sequencing…" : `${side === "BUY" ? "Buy" : "Sell"} ${symbol}`}</button>
      <div className="entry-status"><span className="status-light" />{message}</div>
    </Panel>
  );
}
