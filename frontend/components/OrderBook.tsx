import { price } from "@/lib/format";
import type { Level } from "@/types/market";
import { Panel } from "./Panel";

function LevelRow({ level, side, max }: { level: Level; side: "bid" | "ask"; max: number }) {
  const width = `${Math.max(4, (level.quantity / max) * 100)}%`;
  return (
    <div className={`level-row ${side}`}>
      <span className="depth-fill" style={{ width }} />
      <span className="level-price">{price(level.price_ticks)}</span>
      <span>{level.quantity.toLocaleString()}</span>
      <span className="muted">{level.order_count}</span>
    </div>
  );
}

export function OrderBook({ bids, asks, spread }: { bids: Level[]; asks: Level[]; spread: number | null }) {
  const visibleAsks = asks.slice(0, 8).reverse();
  const visibleBids = bids.slice(0, 8);
  const max = Math.max(1, ...bids.map((item) => item.quantity), ...asks.map((item) => item.quantity));
  return (
    <Panel title="Order Book" eyebrow="L2 · PRICE–TIME" className="order-book-panel" action={<span className="tag">16 levels</span>}>
      <div className="ladder-head"><span>Price</span><span>Size</span><span>#</span></div>
      <div className="levels asks">
        {visibleAsks.map((level) => <LevelRow key={level.price_ticks} level={level} side="ask" max={max} />)}
      </div>
      <div className="spread-row">
        <span>SPREAD</span><strong>{spread === null ? "—" : `${spread} ticks`}</strong><span className="pulse-dot" />
      </div>
      <div className="levels bids">
        {visibleBids.map((level) => <LevelRow key={level.price_ticks} level={level} side="bid" max={max} />)}
      </div>
    </Panel>
  );
}

