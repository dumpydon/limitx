from __future__ import annotations

import random

from limitx.domain.commands import (
    CancelOrder,
    ModifyOrder,
    NewOrder,
    command_from_dict,
    command_to_dict,
)
from limitx.domain.enums import EventType, OrderType, Side, TimeInForce
from limitx.domain.order import Order
from limitx.engine.order_book import OrderBook
from limitx.reference.matcher import ReferenceBook


def production_live(book: OrderBook):
    return sorted(
        (
            order.order_id,
            order.side.value,
            int(order.price_ticks or 0),
            order.remaining_qty,
            order.filled_qty,
        )
        for order in book.iter_live_orders()
    )


def production_depth(book: OrderBook):
    depth = book.depth()
    return {
        side: [
            (level["price_ticks"], level["quantity"], level["order_count"]) for level in depth[side]
        ]
        for side in ("bids", "asks")
    }


def test_thousands_of_seeded_commands_match_reference():
    for seed in range(12):
        rng = random.Random(seed)
        book = OrderBook("BTC-USD", audit_mode=True)
        reference = ReferenceBook("BTC-USD")
        known: list[str] = []
        for index in range(220):
            action = rng.random()
            if action < 0.72:
                order_id = f"{seed}-{index}"
                known.append(order_id)
                side = rng.choice([Side.BUY, Side.SELL])
                order_type = rng.choices([OrderType.LIMIT, OrderType.MARKET], [8, 2])[0]
                tif = (
                    rng.choice([TimeInForce.IOC, TimeInForce.FOK])
                    if order_type is OrderType.MARKET
                    else rng.choice(list(TimeInForce))
                )
                command = NewOrder(
                    Order(
                        order_id,
                        "BTC-USD",
                        f"acct-{rng.randrange(6)}",
                        side,
                        order_type,
                        rng.randint(1, 25),
                        rng.randint(96, 104) if order_type is OrderType.LIMIT else None,
                        tif,
                    )
                )
            elif action < 0.88:
                command = CancelOrder("BTC-USD", rng.choice(known or ["missing"]))
            else:
                command = ModifyOrder(
                    "BTC-USD",
                    rng.choice(known or ["missing"]),
                    rng.randint(1, 30),
                    rng.randint(96, 104),
                )
            reference_command = command_from_dict(command_to_dict(command))
            expected_trades = reference.process(reference_command)
            events = book.process(command)
            actual_trades = [
                (
                    str(event.data["maker_order_id"]),
                    str(event.data["taker_order_id"]),
                    int(event.data["price_ticks"]),
                    int(event.data["quantity"]),
                )
                for event in events
                if event.event_type is EventType.TRADE_EXECUTED
            ]
            assert actual_trades == expected_trades, (
                f"seed={seed}, index={index}, command={command}"
            )
            assert production_live(book) == reference.canonical_live(), (
                f"seed={seed}, index={index}, command={command}"
            )
            assert production_depth(book) == reference.canonical_depth()
