from __future__ import annotations

from typing import Any

from limitx.engine.order_book import OrderBook
from limitx.replay.journal import EventJournal

STAGE_LABELS = {
    "ORDER_ACCEPTED": "Sequenced and accepted",
    "ORDER_REJECTED": "Validation or matching-policy rejection",
    "RISK_REJECTED": "Pre-trade risk rejection",
    "TRADE_EXECUTED": "Matched against resting liquidity",
    "ORDER_PARTIALLY_FILLED": "Partial fill recorded",
    "ORDER_FILLED": "Order fully filled",
    "ORDER_CANCELLED": "Order cancelled",
    "CANCEL_REJECTED": "Cancel rejected",
    "ORDER_MODIFIED": "Order modified",
    "MODIFY_REJECTED": "Modification rejected",
}


def _command_mentions(command: dict[str, object], order_id: str) -> bool:
    if command.get("command") == "NEW":
        order = command.get("order")
        return isinstance(order, dict) and order.get("order_id") == order_id
    return command.get("order_id") == order_id


def _event_mentions(event: dict[str, Any], order_id: str) -> bool:
    return event.get("order_id") == order_id or order_id in {
        event.get("maker_order_id"),
        event.get("taker_order_id"),
    }


def explain_order(book: OrderBook, journal: EventJournal, order_id: str) -> dict[str, Any] | None:
    commands = [
        {
            "command_sequence": entry.command_sequence,
            "command": entry.command,
        }
        for entry in journal.entries
        if _command_mentions(entry.command, order_id)
    ]
    events = sorted(
        (
            event
            for entry in journal.entries
            for event in entry.events
            if _event_mentions(event, order_id)
        ),
        key=lambda event: int(event["sequence"]),
    )
    order = book.orders.get(order_id)
    if not commands and not events and order is None:
        return None
    first_command = commands[0]["command"] if commands else {}
    order_payload = first_command.get("order") if isinstance(first_command, dict) else None
    requested = int(order_payload.get("quantity", 0)) if isinstance(order_payload, dict) else 0
    trades = [event for event in events if event.get("type") == "TRADE_EXECUTED"]
    trade_quantity = sum(int(event["quantity"]) for event in trades)
    notional = sum(int(event["price_ticks"]) * int(event["quantity"]) for event in trades)
    relevant_trade_quantity = (
        trade_quantity
        if any(event.get("taker_order_id") == order_id for event in trades)
        else sum(
            int(event["quantity"]) for event in trades if event.get("maker_order_id") == order_id
        )
    )
    rejection = next(
        (event for event in events if event.get("type") in {"ORDER_REJECTED", "RISK_REJECTED"}),
        None,
    )
    if rejection and rejection.get("reason") == "FOK_NOT_FILLABLE":
        explanation = (
            f"FOK requested {rejection.get('requested_quantity')} units, but only "
            f"{rejection.get('eligible_quantity')} units were eligible within its limit. "
            "The preflight rejected it before any book mutation."
        )
    elif rejection and rejection.get("reason") == "POST_ONLY_WOULD_TRADE":
        explanation = (
            f"Post-only price {rejection.get('order_price_ticks')} ticks crossed the opposing "
            f"best price {rejection.get('opposing_best_ticks')} ticks, so it was rejected."
        )
    elif rejection and rejection.get("type") == "RISK_REJECTED":
        explanation = (
            f"Risk rule {rejection.get('reason')} rejected observed value "
            f"{rejection.get('observed')} against threshold {rejection.get('threshold')}."
        )
    elif trades and order and order.is_live and order.remaining_qty:
        explanation = (
            f"The order executed {relevant_trade_quantity} units across "
            f"{len({event['price_ticks'] for event in trades})} eligible price levels; "
            f"{order.remaining_qty} units remain resting under its time-in-force policy."
        )
    elif trades and order and order.status.value == "CANCELLED":
        explanation = (
            f"The order executed {relevant_trade_quantity} units at eligible resting prices, "
            f"then its unfilled {order.remaining_qty}-unit remainder was cancelled by its "
            "time-in-force policy."
        )
    elif trades:
        explanation = (
            f"The order executed {relevant_trade_quantity} units across "
            f"{len({event['price_ticks'] for event in trades})} price levels at resting prices."
        )
    elif order and order.is_live:
        explanation = (
            "Validation and pre-trade risk passed, but no opposing liquidity was eligible at "
            f"the order price. Its remaining {order.remaining_qty} units rest in FIFO priority "
            f"at {order.price_ticks} ticks."
        )
    elif order and order.status.value == "CANCELLED":
        was_modified = any(event.get("type") == "ORDER_MODIFIED" for event in events)
        explanation = (
            "The order passed validation and risk, entered the FIFO book"
            f"{' and was modified under the documented priority rule' if was_modified else ''}, "
            "then a user cancellation unlinked its live node without an execution."
        )
    else:
        explanation = "The order was sequenced without an execution in the inspected event history."

    timeline = [
        {
            "sequence": int(event["sequence"]),
            "evidence_id": f"event:{event['sequence']}",
            "type": event["type"],
            "stage": STAGE_LABELS.get(str(event["type"]), str(event["type"])),
            "facts": event,
        }
        for event in events
    ]
    accepted_event = next(
        (event for event in events if event.get("type") == "ORDER_ACCEPTED"), None
    )
    pipeline = []
    if commands:
        pipeline.append(
            {
                "stage": "Command received",
                "evidence_id": f"command:{commands[0]['command_sequence']}",
                "basis": "Canonical append-only command journal",
            }
        )
    if accepted_event:
        for stage in ("Validation passed", "Risk accepted", "Sequenced by matcher"):
            pipeline.append(
                {
                    "stage": stage,
                    "evidence_id": f"event:{accepted_event['sequence']}",
                    "basis": "ORDER_ACCEPTED is emitted only after gateway checks pass",
                }
            )
    pipeline.extend(
        {
            "stage": STAGE_LABELS.get(str(event["type"]), str(event["type"])),
            "evidence_id": f"event:{event['sequence']}",
            "basis": str(event["type"]),
        }
        for event in events
        if event.get("type") != "ORDER_ACCEPTED"
    )
    return {
        "order_id": order_id,
        "symbol": book.symbol,
        "status": order.status.value if order else str(events[-1].get("type", "UNKNOWN")),
        "requested_quantity": requested,
        "filled_quantity": order.filled_qty if order else relevant_trade_quantity,
        "remaining_quantity": order.remaining_qty if order else 0,
        "explanation": explanation,
        "commands": commands,
        "timeline": timeline,
        "pipeline": pipeline,
        "execution": {
            "trade_count": len(trades),
            "levels_consumed": sorted({int(event["price_ticks"]) for event in trades}),
            "vwap_ticks": notional / trade_quantity if trade_quantity else None,
            "trades": trades,
        },
    }
