from __future__ import annotations

from dataclasses import dataclass

from limitx.domain.enums import OrderStatus, OrderType, Side, TimeInForce


@dataclass(slots=True)
class Order:
    order_id: str
    symbol: str
    account_id: str
    side: Side
    order_type: OrderType
    quantity: int
    price_ticks: int | None = None
    time_in_force: TimeInForce = TimeInForce.GTC
    status: OrderStatus = OrderStatus.NEW
    remaining_qty: int = 0
    filled_qty: int = 0
    accepted_sequence: int = 0
    created_at_ns: int = 0

    def __post_init__(self) -> None:
        if not self.remaining_qty:
            self.remaining_qty = self.quantity

    @property
    def is_live(self) -> bool:
        return self.status in {OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}

    def as_dict(self) -> dict[str, object]:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "account_id": self.account_id,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "time_in_force": self.time_in_force.value,
            "price_ticks": self.price_ticks,
            "quantity": self.quantity,
            "remaining_qty": self.remaining_qty,
            "filled_qty": self.filled_qty,
            "status": self.status.value,
            "accepted_sequence": self.accepted_sequence,
            "created_at_ns": self.created_at_ns,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Order:
        return cls(
            order_id=str(data["order_id"]),
            symbol=str(data["symbol"]),
            account_id=str(data["account_id"]),
            side=Side(str(data["side"])),
            order_type=OrderType(str(data["order_type"])),
            quantity=int(str(data["quantity"])),
            price_ticks=(
                int(str(data["price_ticks"])) if data.get("price_ticks") is not None else None
            ),
            time_in_force=TimeInForce(str(data["time_in_force"])),
            status=OrderStatus(str(data.get("status", OrderStatus.NEW))),
            remaining_qty=int(str(data.get("remaining_qty", data["quantity"]))),
            filled_qty=int(str(data.get("filled_qty", 0))),
            accepted_sequence=int(str(data.get("accepted_sequence", 0))),
            created_at_ns=int(str(data.get("created_at_ns", 0))),
        )
