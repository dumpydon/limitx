import { price } from "@/lib/format";
import type { Trade } from "@/types/market";
import { Panel } from "./Panel";

export function Trades({ trades }: { trades: Trade[] }) {
  return (
    <Panel title="Recent trades" eyebrow="Execution tape" action={<span className="tag">{trades.length} prints</span>}>
      <div className="table-head trades-grid"><span>Time</span><span>Price</span><span>Size</span><span>Side</span><span>Seq</span></div>
      <div className="table-scroll">
        {trades.slice(0, 12).map((trade) => (
          <div className="table-row trades-grid trade-flash" key={`${trade.sequence}-${trade.maker_order_id}`}>
            <span className="mono muted">T+{(trade.logical_time_ns / 1_000_000_000).toFixed(6)}</span><span className={trade.aggressor_side === "BUY" ? "buy-text" : "sell-text"}>{price(trade.price_ticks)}</span><span>{trade.quantity}</span><span className={`side-pill ${trade.aggressor_side.toLowerCase()}`}>{trade.aggressor_side}</span><span className="mono muted">{trade.sequence}</span>
          </div>
        ))}
        {!trades.length ? <div className="empty">No executions yet. Run a market scenario.</div> : null}
      </div>
    </Panel>
  );
}
