"use client";

import { useState } from "react";
import { price } from "@/lib/format";
import type { Level } from "@/types/market";
import { Panel } from "./Panel";

function points(levels: Level[], width: number, height: number, reverse = false): string {
  if (!levels.length) return "";
  let cumulative = 0;
  const totals = levels.map((level) => (cumulative += level.quantity));
  const max = Math.max(...totals, 1);
  const source = reverse ? [...totals].reverse() : totals;
  return source.map((total, index) => `${(index / Math.max(source.length - 1, 1)) * width},${height - (total / max) * (height - 20)}`).join(" ");
}

export function DepthChart({ bids, asks }: { bids: Level[]; asks: Level[] }) {
  const [visibleLevels, setVisibleLevels] = useState(10);
  const [hover, setHover] = useState<{ side: string; level: Level; cumulative: number } | null>(null);
  const depth = visibleLevels === 0 ? Math.max(bids.length, asks.length) : visibleLevels;
  const visibleBids = bids.slice(0, depth);
  const visibleAsks = asks.slice(0, depth);
  const bidPoints = points(visibleBids, 300, 180, true);
  const askPoints = points(visibleAsks, 300, 180);
  const bidDots = visibleBids.map((level, index) => ({ level, cumulative: visibleBids.slice(0, index + 1).reduce((sum, item) => sum + item.quantity, 0), x: 300 - (index / Math.max(visibleBids.length - 1, 1)) * 300 }));
  const askDots = visibleAsks.map((level, index) => ({ level, cumulative: visibleAsks.slice(0, index + 1).reduce((sum, item) => sum + item.quantity, 0), x: 340 + (index / Math.max(visibleAsks.length - 1, 1)) * 300 }));
  return (
    <Panel title="Market depth" eyebrow="Cumulative liquidity" className="depth-panel" action={<div className="depth-range">{[10, 25, 50, 0].map((item) => <button key={item} className={visibleLevels === item ? "active" : ""} onClick={() => setVisibleLevels(item)}>{item || "All"}</button>)}</div>}>
      <div className="chart-wrap">
        <svg viewBox="0 0 640 220" role="img" aria-label="Cumulative bid and ask depth chart">
          <defs>
            <linearGradient id="bid-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#39d5a1" stopOpacity=".32" /><stop offset="1" stopColor="#39d5a1" stopOpacity="0" /></linearGradient>
            <linearGradient id="ask-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ff6c7d" stopOpacity=".3" /><stop offset="1" stopColor="#ff6c7d" stopOpacity="0" /></linearGradient>
          </defs>
          {[30, 80, 130, 180].map((y) => <line key={y} x1="0" y1={y} x2="640" y2={y} className="grid-line" />)}
          {bidPoints ? <><polyline points={bidPoints} transform="translate(0 10)" className="bid-line" /><polygon points={`0,210 ${bidPoints} 300,210`} fill="url(#bid-area)" /></> : null}
          {askPoints ? <><polyline points={askPoints} transform="translate(340 10)" className="ask-line" /><polygon points={`340,210 ${askPoints.split(" ").map((p) => { const [x,y] = p.split(","); return `${Number(x)+340},${Number(y)+10}`; }).join(" ")} 640,210`} fill="url(#ask-area)" /></> : null}
          <line x1="320" y1="8" x2="320" y2="210" className="mid-line" />
          {[...bidDots.map((dot) => ({ ...dot, side: "BID" })), ...askDots.map((dot) => ({ ...dot, side: "ASK" }))].map((dot) => <circle key={`${dot.side}-${dot.level.price_ticks}`} cx={dot.x} cy="110" r="10" className="depth-hit" onMouseEnter={() => setHover(dot)} onMouseLeave={() => setHover(null)}><title>{`${dot.side} ${price(dot.level.price_ticks)} · level ${dot.level.quantity} · cumulative ${dot.cumulative} · ${dot.level.order_count} orders`}</title></circle>)}
        </svg>
        <div className="chart-axis"><span>{price(visibleBids.at(-1)?.price_ticks)}</span><strong>{hover ? `${hover.side} ${price(hover.level.price_ticks)} · ${hover.cumulative} cumulative` : "Mid · hover for level details"}</strong><span>{price(visibleAsks.at(-1)?.price_ticks)}</span></div>
      </div>
    </Panel>
  );
}
