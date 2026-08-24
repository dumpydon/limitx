import { price } from "@/lib/format";
import type { Level } from "@/types/market";
import { Panel } from "./Panel";

function LevelRow({
  level,
  side,
  max,
  total,
  best,
}: {
  level: Level;
  side: "bid" | "ask";
  max: number;
  total: number;
  best: boolean;
}) {
  const width = `${Math.max(4, (level.quantity / max) * 100)}%`;
  return (
    <div className={`level-row ${side} ${best ? "best-level" : ""}`}>
      <span className="depth-fill" style={{ width }} />
      <span className="level-price">{price(level.price_ticks)}</span>
      <span>{level.quantity.toLocaleString()}</span>
      <span>{total.toLocaleString()}</span>
      <span className="muted">{level.order_count}</span>
      {best ? <span className="best-label" tabIndex={0} aria-label={side === "bid" ? "Best bid definition" : "Best ask definition"}>{side === "bid" ? "Best bid" : "Best ask"}<i className="best-tooltip" role="tooltip">{side === "bid" ? "The highest price someone is willing to buy. Example: a market sell reaches this price first." : "The lowest price someone is willing to sell. Example: a market buy reaches this price first."}</i></span> : null}
    </div>
  );
}

export function OrderBook({
  bids,
  asks,
  spread,
  mid,
}: {
  bids: Level[];
  asks: Level[];
  spread: number | null;
  mid: number | null;
}) {
  const askSlice = asks.slice(0, 8);
  const bidSlice = bids.slice(0, 8);
  const asksWithTotal = askSlice.map((level, index) => ({ level, total: askSlice.slice(0, index + 1).reduce((sum, item) => sum + item.quantity, 0) }));
  const bidsWithTotal = bidSlice.map((level, index) => ({ level, total: bidSlice.slice(0, index + 1).reduce((sum, item) => sum + item.quantity, 0) }));
  const visibleAsks = [...asksWithTotal].reverse();
  const max = Math.max(1, ...bids.map((item) => item.quantity), ...asks.map((item) => item.quantity));
  const spreadBps = spread !== null && mid ? (spread / mid) * 10_000 : null;
  return (
    <Panel title="Order book" eyebrow="L2 · price-time" className="order-book-panel" action={<span className="tag">16 levels</span>}>
      <div className="ladder-head"><span>Price</span><span>Size</span><span>Total</span><span>Orders</span></div>
      <div className="levels asks">
        {visibleAsks.map(({ level, total }) => <LevelRow key={level.price_ticks} level={level} side="ask" max={max} total={total} best={level.price_ticks === asks[0]?.price_ticks} />)}
      </div>
      <div className="spread-row">
        <span>SPREAD</span><strong>{spread === null ? "—" : `${spread} ticks`}</strong><span>MID</span><strong>{price(mid)}</strong><span>BPS</span><strong>{spreadBps === null ? "—" : spreadBps.toFixed(3)}</strong>
      </div>
      <div className="levels bids">
        {bidsWithTotal.map(({ level, total }) => <LevelRow key={level.price_ticks} level={level} side="bid" max={max} total={total} best={level.price_ticks === bids[0]?.price_ticks} />)}
      </div>
    </Panel>
  );
}
