from __future__ import annotations

from dataclasses import dataclass

from limitx.domain.order import Order


@dataclass(frozen=True, slots=True)
class NewOrder:
    order: Order


@dataclass(frozen=True, slots=True)
class CancelOrder:
    symbol: str
    order_id: str
    account_id: str | None = None


@dataclass(frozen=True, slots=True)
class ModifyOrder:
    symbol: str
    order_id: str
    new_quantity: int
    new_price_ticks: int | None = None
    account_id: str | None = None


Command = NewOrder | CancelOrder | ModifyOrder


def command_to_dict(command: Command) -> dict[str, object]:
    if isinstance(command, NewOrder):
        return {"command": "NEW", "order": command.order.as_dict()}
    if isinstance(command, CancelOrder):
        return {
            "command": "CANCEL",
            "symbol": command.symbol,
            "order_id": command.order_id,
            "account_id": command.account_id,
        }
    return {
        "command": "MODIFY",
        "symbol": command.symbol,
        "order_id": command.order_id,
        "new_quantity": command.new_quantity,
        "new_price_ticks": command.new_price_ticks,
        "account_id": command.account_id,
    }


def command_from_dict(data: dict[str, object]) -> Command:
    kind = str(data["command"])
    if kind == "NEW":
        order_data = data["order"]
        if not isinstance(order_data, dict):
            raise ValueError("order must be an object")
        order = Order.from_dict(order_data)
        order.status = order.status.NEW
        order.remaining_qty = order.quantity
        order.filled_qty = 0
        order.accepted_sequence = 0
        return NewOrder(order)
    if kind == "CANCEL":
        return CancelOrder(
            symbol=str(data["symbol"]),
            order_id=str(data["order_id"]),
            account_id=str(data["account_id"]) if data.get("account_id") else None,
        )
    if kind == "MODIFY":
        return ModifyOrder(
            symbol=str(data["symbol"]),
            order_id=str(data["order_id"]),
            new_quantity=int(str(data["new_quantity"])),
            new_price_ticks=(
                int(str(data["new_price_ticks"]))
                if data.get("new_price_ticks") is not None
                else None
            ),
            account_id=str(data["account_id"]) if data.get("account_id") else None,
        )
    raise ValueError(f"unknown command type: {kind}")
