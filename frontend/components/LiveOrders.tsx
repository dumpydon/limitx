"use client";

import { price } from "@/lib/format";
import type { LiveOrder } from "@/types/market";
import { Panel } from "./Panel";

export function LiveOrders({ orders, onCancel }: { orders: LiveOrder[]; onCancel: (order: LiveOrder) => void }) {
  return (
    <Panel title="My Live Orders" eyebrow="DIRECT CANCEL PATH" action={<span className="tag">{orders.length} resting</span>}>
      <div className="table-head orders-grid"><span>ID</span><span>Side</span><span>Price</span><span>Remaining</span><span>Priority</span><span /></div>
      <div className="table-scroll compact-table">
        {orders.map((order) => <div className="table-row orders-grid" key={order.order_id}><span className="mono truncate">{order.order_id}</span><span className={order.side === "BUY" ? "buy-text" : "sell-text"}>{order.side}</span><span>{price(order.price_ticks)}</span><span>{order.remaining_qty} / {order.quantity}</span><span className="mono muted">{order.accepted_sequence}</span><button className="cancel-mini" onClick={() => onCancel(order)}>Cancel</button></div>)}
        {!orders.length ? <div className="empty">No simulated orders resting for demo-user.</div> : null}
      </div>
    </Panel>
  );
}

