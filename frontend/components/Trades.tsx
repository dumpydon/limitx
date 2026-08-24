import { price } from "@/lib/format";
import type { Trade } from "@/types/market";
import { Panel } from "./Panel";

export function Trades({ trades }: { trades: Trade[] }) {
  return (
    <Panel title="Recent Trades" eyebrow="EXECUTION TAPE" action={<span className="tag">{trades.length} prints</span>}>
      <div className="table-head trades-grid"><span>Seq</span><span>Price</span><span>Size</span><span>Aggressor</span></div>
      <div className="table-scroll">
        {trades.slice(0, 12).map((trade) => (
          <div className="table-row trades-grid" key={`${trade.sequence}-${trade.maker_order_id}`}>
            <span className="mono muted">{trade.sequence}</span><span className={trade.aggressor_side === "BUY" ? "buy-text" : "sell-text"}>{price(trade.price_ticks)}</span><span>{trade.quantity}</span><span className={`side-pill ${trade.aggressor_side.toLowerCase()}`}>{trade.aggressor_side}</span>
          </div>
        ))}
        {!trades.length ? <div className="empty">No executions yet. Run a market scenario.</div> : null}
      </div>
    </Panel>
  );
}

