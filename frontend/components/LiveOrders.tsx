"use client";

import { price } from "@/lib/format";
import type { LiveOrder } from "@/types/market";
import { Panel } from "./Panel";

export function LiveOrders({ orders, onCancel, onModify, onInspect }: { orders: LiveOrder[]; onCancel: (order: LiveOrder) => void; onModify: (order: LiveOrder) => void; onInspect: (orderId: string) => void }) {
  return (
    <Panel title="Open orders" eyebrow="Direct cancel lookup" action={<span className="tag">{orders.length} resting</span>}>
      <div className="table-head orders-grid"><span>ID</span><span>Side</span><span>Price</span><span>Remaining</span><span>Priority</span><span /></div>
      <div className="table-scroll compact-table">
        {orders.map((order) => <div className="table-row orders-grid" key={order.order_id}><button className="order-link mono truncate" onClick={() => onInspect(order.order_id)}>{order.order_id}</button><span className={order.side === "BUY" ? "buy-text" : "sell-text"}>{order.side}</span><span>{price(order.price_ticks)}</span><span>{order.remaining_qty} / {order.quantity}</span><span className="mono muted">{order.accepted_sequence}</span><div className="order-actions"><button onClick={() => onModify(order)}>−1</button><button className="cancel-mini" onClick={() => onCancel(order)}>Cancel</button></div></div>)}
        {!orders.length ? <div className="empty">No simulated orders resting for demo-user.</div> : null}
      </div>
    </Panel>
  );
}
