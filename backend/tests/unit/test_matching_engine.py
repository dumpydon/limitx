from __future__ import annotations

import pytest

from limitx.domain.enums import EventType, OrderStatus, OrderType, Side, TimeInForce
from limitx.engine.order_book import OrderBook


def event_types(events):
    return [event.event_type for event in events]


def test_non_crossing_limit_rests_and_exact_cross_uses_resting_price(make_order):
    book = OrderBook("BTC-USD", audit_mode=True)
    ask = make_order("A1", Side.SELL, 10, 101)
    bid = make_order("B1", Side.BUY, 10, 100)
    book.submit(ask)
    book.submit(bid)
    assert book.best_bid == 100
    assert book.best_ask == 101

    events = book.submit(make_order("B2", Side.BUY, 10, 105))
    trade = next(event for event in events if event.event_type is EventType.TRADE_EXECUTED)
    assert trade.data["price_ticks"] == 101
    assert ask.status is OrderStatus.FILLED
    assert book.best_ask is None


def test_partial_multi_level_fill_and_fifo(make_order):
    book = OrderBook("BTC-USD", audit_mode=True)
    for order_id, quantity, price in [("A1", 4, 101), ("A2", 6, 101), ("A3", 8, 102)]:
        book.submit(make_order(order_id, Side.SELL, quantity, price))
    events = book.submit(make_order("B1", Side.BUY, 12, 102))
    trades = [event for event in events if event.event_type is EventType.TRADE_EXECUTED]
    assert [
        (e.data["maker_order_id"], e.data["quantity"], e.data["price_ticks"]) for e in trades
    ] == [
        ("A1", 4, 101),
        ("A2", 6, 101),
        ("A3", 2, 102),
    ]
    assert book.live_orders["A3"].order.remaining_qty == 6


def test_market_empty_and_ioc_remainder_cancel(make_order):
    book = OrderBook("BTC-USD", audit_mode=True)
    market = make_order(
        "M1",
        Side.BUY,
        10,
        None,
        order_type=OrderType.MARKET,
        tif=TimeInForce.IOC,
    )
    events = book.submit(market)
    assert EventType.ORDER_CANCELLED in event_types(events)
    assert market.status is OrderStatus.CANCELLED
    assert not book.live_orders

    book.submit(make_order("A1", Side.SELL, 4, 101))
    ioc = make_order("I1", Side.BUY, 10, 101, tif=TimeInForce.IOC)
    book.submit(ioc)
    assert ioc.filled_qty == 4
    assert ioc.remaining_qty == 6
    assert ioc.status is OrderStatus.CANCELLED


def test_fok_preflight_is_atomic(make_order):
    book = OrderBook("BTC-USD", audit_mode=True)
    book.submit(make_order("A1", Side.SELL, 4, 101))
    book.submit(make_order("A2", Side.SELL, 4, 102))
    before = book.canonical_state()
    fok = make_order("F1", Side.BUY, 9, 102, tif=TimeInForce.FOK)
    events = book.submit(fok)
    assert events[0].data["reason"] == "FOK_NOT_FILLABLE"
    assert book.canonical_state()["bids"] == before["bids"]
    assert book.canonical_state()["asks"] == before["asks"]
    assert not book.trades

    fillable = make_order("F2", Side.BUY, 8, 102, tif=TimeInForce.FOK)
    book.submit(fillable)
    assert fillable.status is OrderStatus.FILLED


def test_post_only_cross_rejects_without_mutation(make_order):
    book = OrderBook("BTC-USD", audit_mode=True)
    book.submit(make_order("A1", Side.SELL, 4, 101))
    order = make_order("P1", Side.BUY, 2, 101, tif=TimeInForce.POST_ONLY)
    events = book.submit(order)
    assert events[0].data["reason"] == "POST_ONLY_WOULD_TRADE"
    assert order.status is OrderStatus.REJECTED
    assert book.best_ask == 101


def test_cancel_direct_lookup_unknown_double_and_last_level(make_order):
    book = OrderBook("BTC-USD", audit_mode=True)
    book.submit(make_order("B1", Side.BUY, 5, 100))
    events = book.cancel("B1")
    assert events[0].event_type is EventType.ORDER_CANCELLED
    assert book.best_bid is None
    assert book.cancel("B1")[0].event_type is EventType.CANCEL_REJECTED
    assert book.cancel("missing")[0].event_type is EventType.CANCEL_REJECTED


def test_duplicate_invalid_quantity_and_price(make_order):
    book = OrderBook("BTC-USD", audit_mode=True)
    book.submit(make_order("B1", Side.BUY, 5, 100))
    assert book.submit(make_order("B1", Side.BUY, 5, 99))[0].data["reason"] == "DUPLICATE_ORDER_ID"
    assert book.submit(make_order("Z", Side.BUY, 0, 99))[0].data["reason"] == "INVALID_QUANTITY"
    assert book.submit(make_order("P", Side.BUY, 1, 0))[0].data["reason"] == "INVALID_PRICE"


def test_self_trade_prevention_cancels_taker(make_order):
    book = OrderBook("BTC-USD", audit_mode=True)
    book.submit(make_order("A1", Side.SELL, 5, 101, account="same"))
    taker = make_order("B1", Side.BUY, 5, 101, account="same")
    events = book.submit(taker)
    assert not book.trades
    assert any(event.data.get("reason") == "SELF_TRADE_PREVENTION" for event in events)
    assert book.best_ask == 101


def test_modify_priority_semantics(make_order):
    book = OrderBook("BTC-USD", audit_mode=True)
    first = make_order("B1", Side.BUY, 10, 100)
    second = make_order("B2", Side.BUY, 10, 100)
    book.submit(first)
    book.submit(second)
    first_priority = first.accepted_sequence
    event = book.modify("B1", 8)[0]
    assert event.data["priority_retained"] is True
    assert first.accepted_sequence == first_priority
    book.modify("B1", 12)
    assert first.accepted_sequence > second.accepted_sequence
    book.submit(make_order("A1", Side.SELL, 10, 100))
    assert book.trades[-1]["maker_order_id"] == "B2"


def test_modify_price_can_cross_and_unknown_rejects(make_order):
    book = OrderBook("BTC-USD", audit_mode=True)
    book.submit(make_order("A1", Side.SELL, 5, 101))
    book.submit(make_order("B1", Side.BUY, 5, 99))
    events = book.modify("B1", 5, 101)
    assert any(event.event_type is EventType.TRADE_EXECUTED for event in events)
    assert book.modify("unknown", 1)[0].event_type is EventType.MODIFY_REJECTED


def test_snapshot_roundtrip_and_tamper_detection(make_order):
    book = OrderBook("BTC-USD", audit_mode=True)
    book.submit(make_order("B1", Side.BUY, 5, 100))
    book.submit(make_order("A1", Side.SELL, 8, 102))
    restored = OrderBook.from_snapshot(book.snapshot(), audit_mode=True)
    assert restored.canonical_state() == book.canonical_state()
    assert restored.checksum() == book.checksum()
    bad = book.snapshot()
    bad["checksum"] = "wrong"
    with pytest.raises(ValueError, match="checksum"):
        OrderBook.from_snapshot(bad)
