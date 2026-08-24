from __future__ import annotations

from collections import Counter
from typing import Any

from limitx.domain.enums import EventType, Side
from limitx.engine.order_book import OrderBook


def calculate_metrics(book: OrderBook) -> dict[str, Any]:
    depth = book.depth(20)
    bid_qty = sum(level["quantity"] for level in depth["bids"])
    ask_qty = sum(level["quantity"] for level in depth["asks"])
    total_depth = bid_qty + ask_qty
    volume = sum(int(trade["quantity"]) for trade in book.trades)
    notional = sum(int(trade["price_ticks"]) * int(trade["quantity"]) for trade in book.trades)
    buy_volume = sum(
        int(trade["quantity"]) for trade in book.trades if trade["aggressor_side"] == Side.BUY.value
    )
    event_counts = Counter(event.event_type for event in book.events)
    accepted = event_counts[EventType.ORDER_ACCEPTED]
    cancels = event_counts[EventType.ORDER_CANCELLED]
    filled = event_counts[EventType.ORDER_FILLED]
    bid, ask = book.best_bid, book.best_ask
    best_bid_qty = depth["bids"][0]["quantity"] if depth["bids"] else 0
    best_ask_qty = depth["asks"][0]["quantity"] if depth["asks"] else 0
    top_total = best_bid_qty + best_ask_qty
    microprice_x2 = None
    if bid is not None and ask is not None and top_total:
        microprice_x2 = 2 * (ask * best_bid_qty + bid * best_ask_qty) / top_total
    accepted_at: dict[str, int] = {}
    resting_lifetimes: list[int] = []
    for event in book.events:
        if event.event_type is EventType.ORDER_ACCEPTED and event.order_id:
            accepted_at[event.order_id] = event.logical_time_ns
        elif (
            event.event_type in {EventType.ORDER_FILLED, EventType.ORDER_CANCELLED}
            and event.order_id
        ):
            started = accepted_at.pop(event.order_id, None)
            if started is not None:
                resting_lifetimes.append(event.logical_time_ns - started)
    measured_slippage = [
        (int(trade["slippage_ticks_x2"]), int(trade["quantity"]))
        for trade in book.trades
        if trade.get("slippage_ticks_x2") is not None
    ]
    slippage_quantity = sum(quantity for _, quantity in measured_slippage)
    average_slippage = (
        sum(value * quantity for value, quantity in measured_slippage) / (2 * slippage_quantity)
        if slippage_quantity
        else None
    )
    return {
        "spread_ticks": ask - bid if bid is not None and ask is not None else None,
        "mid_ticks": (bid + ask) / 2 if bid is not None and ask is not None else None,
        "microprice_ticks": microprice_x2 / 2 if microprice_x2 is not None else None,
        "vwap_ticks": notional / volume if volume else None,
        "trade_volume": volume,
        "buy_aggressor_volume": buy_volume,
        "sell_aggressor_volume": volume - buy_volume,
        "order_flow_imbalance": (2 * buy_volume - volume) / volume if volume else 0,
        "depth_imbalance": (bid_qty - ask_qty) / total_depth if total_depth else 0,
        "bid_depth": bid_qty,
        "ask_depth": ask_qty,
        "cancel_to_add_ratio": cancels / accepted if accepted else 0,
        "fill_ratio": filled / accepted if accepted else 0,
        "average_resting_lifetime_ns": (
            sum(resting_lifetimes) / len(resting_lifetimes) if resting_lifetimes else None
        ),
        "average_aggressive_slippage_ticks": average_slippage,
        "last_price_impact_ticks": (
            int(measured_slippage[-1][0]) / 2 if measured_slippage else None
        ),
        "active_orders": len(book.live_orders),
        "bid_levels": len(book.bids),
        "ask_levels": len(book.asks),
    }


def aggressive_slippage(
    trades: list[dict[str, Any]], arrival_mid_ticks: float | None
) -> float | None:
    if not trades or arrival_mid_ticks is None:
        return None
    quantity = sum(int(trade["quantity"]) for trade in trades)
    vwap = sum(int(trade["price_ticks"]) * int(trade["quantity"]) for trade in trades) / quantity
    direction = 1 if trades[0]["aggressor_side"] == Side.BUY.value else -1
    return direction * (vwap - arrival_mid_ticks)
