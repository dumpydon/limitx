"use client";

import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { decimalToTicks, integer, price } from "@/lib/format";
import type { Side } from "@/types/market";
import { Panel } from "./Panel";

interface OrderResponse {
  events: Record<string, unknown>[];
  order: {
    order_id: string;
    status: string;
    quantity: number;
    filled_qty: number;
    remaining_qty: number;
    price_ticks: number | null;
  };
}

function cents(value: bigint): string {
  const whole = value / BigInt(100);
  const fraction = (value % BigInt(100)).toString().padStart(2, "0");
  return `$${whole.toLocaleString("en-US")}.${fraction}`;
}

function humanStatus(value: unknown): string {
  const words = String(value ?? "Processed").replaceAll("_", " ").toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function OrderEntry({
  symbol,
  referencePriceTicks,
  riskLimits,
  onResult,
  onInspect,
  onSidePreview,
}: {
  symbol: string;
  referencePriceTicks: number;
  riskLimits?: { max_order_quantity: number; max_notional_ticks: number };
  onResult: (events: Record<string, unknown>[], orderId: string) => void;
  onInspect: (orderId: string) => void;
  onSidePreview: (side: "buy" | "sell" | null) => void;
}) {
  const [side, setSide] = useState<Side>("BUY");
  const [type, setType] = useState<"LIMIT" | "MARKET">("LIMIT");
  const [tif, setTif] = useState("GTC");
  const [quantity, setQuantity] = useState("25");
  const [orderPrice, setOrderPrice] = useState((referencePriceTicks / 100).toFixed(2));
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Ready for simulated order");
  const [report, setReport] = useState<OrderResponse["order"] | null>(null);

  const quantityValue = Number.parseInt(quantity, 10) || 0;
  const limitTicks = decimalToTicks(orderPrice);
  const estimateTicks = type === "MARKET" ? referencePriceTicks : limitTicks;
  const estimatedNotional = useMemo(
    () => estimateTicks === null ? null : BigInt(estimateTicks) * BigInt(Math.max(0, quantityValue)),
    [estimateTicks, quantityValue],
  );

  async function submit() {
    const ticks = type === "LIMIT" ? decimalToTicks(orderPrice) : null;
    if (type === "LIMIT" && ticks === null) {
      setMessage("Enter a valid price with at most 2 decimals");
      return;
    }
    setBusy(true);
    try {
      const orderId = `LX-${crypto.randomUUID().slice(0, 8).toUpperCase()}`;
      const result = await api<OrderResponse>("/api/orders", {
        method: "POST",
        body: JSON.stringify({
          order_id: orderId,
          symbol,
          account_id: "demo-user",
          side,
          order_type: type,
          time_in_force: tif,
          quantity: Number.parseInt(quantity, 10),
          price_ticks: ticks,
        }),
      });
      onResult(result.events, orderId);
      setReport(result.order);
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
      setMessage(humanStatus(decisive?.type));
    } catch (error) {
      setMessage(error instanceof Error ? error.message.slice(0, 90) : "Order failed");
    } finally {
      setBusy(false);
    }
  }

  const tifs = type === "MARKET" ? ["IOC", "FOK"] : ["GTC", "IOC", "FOK", "POST_ONLY"];
  return (
    <Panel title="Order entry" eyebrow="Simulated · no real routing" className="entry-panel">
      <div className="segmented side-selector">
        <button className={side === "BUY" ? "active buy" : ""} onClick={() => setSide("BUY")} onMouseEnter={() => onSidePreview("buy")} onMouseLeave={() => onSidePreview(null)} onFocus={() => onSidePreview("buy")} onBlur={() => onSidePreview(null)}>BUY</button>
        <button className={side === "SELL" ? "active sell" : ""} onClick={() => setSide("SELL")} onMouseEnter={() => onSidePreview("sell")} onMouseLeave={() => onSidePreview(null)} onFocus={() => onSidePreview("sell")} onBlur={() => onSidePreview(null)}>SELL</button>
      </div>
      <label>Order type<select value={type} onChange={(event) => { const nextType = event.target.value as "LIMIT" | "MARKET"; setType(nextType); if (nextType === "MARKET" && !["IOC", "FOK"].includes(tif)) setTif("IOC"); }}><option value="LIMIT">Limit</option><option value="MARKET">Market</option></select></label>
      <label>Quantity<input inputMode="numeric" value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label>
      <label>Price <span>USD · 0.01 tick</span><input disabled={type === "MARKET"} inputMode="decimal" value={orderPrice} onChange={(event) => setOrderPrice(event.target.value)} /></label>
      <label>Time in force<select value={tif} onChange={(event) => setTif(event.target.value)}>{tifs.map((item) => <option key={item}>{item}</option>)}</select></label>
      <div className="ticket-estimate">
        <span>Estimated notional</span>
        <strong>{estimatedNotional === null ? "Market depth dependent" : `${integer(quantityValue)} × ${price(estimateTicks)} ≈ ${cents(estimatedNotional)}`}</strong>
        <small>Simulated · exact integer tick arithmetic</small>
      </div>
      <div className="ticket-risk">
        <span>Max size <b>{integer(riskLimits?.max_order_quantity)}</b></span>
        <span>Max notional <b>{riskLimits ? cents(BigInt(riskLimits.max_notional_ticks)) : "—"}</b></span>
      </div>
      <button className={`submit-order ${side.toLowerCase()}`} disabled={busy} onClick={() => void submit()} onMouseEnter={() => onSidePreview(side.toLowerCase() as "buy" | "sell")} onMouseLeave={() => onSidePreview(null)} onFocus={() => onSidePreview(side.toLowerCase() as "buy" | "sell")} onBlur={() => onSidePreview(null)}>{busy ? "Sequencing…" : `${side === "BUY" ? "Buy" : "Sell"} ${symbol}`}</button>
      <div className="entry-status" aria-live="polite"><span className="status-light" />{message}</div>
      {report ? <div className="execution-report"><div><span>Execution report</span><b>{humanStatus(report.status)}</b></div><div><span>Filled</span><strong>{report.filled_qty} / {report.quantity}</strong></div><div><span>Resting</span><strong>{report.remaining_qty ? `${report.remaining_qty} @ ${price(report.price_ticks)}` : "None"}</strong></div><button onClick={() => onInspect(report.order_id)}>Inspect lifecycle →</button></div> : null}
    </Panel>
  );
}
