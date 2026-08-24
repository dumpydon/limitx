from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from limitx.domain.commands import CancelOrder, Command, ModifyOrder, NewOrder
from limitx.domain.enums import OrderType, SelfTradePolicy, Side, TimeInForce


@dataclass(slots=True)
class ReferenceOrder:
    order_id: str
    account_id: str
    side: Side
    order_type: OrderType
    tif: TimeInForce
    price: int | None
    quantity: int
    remaining: int
    filled: int
    priority: int


class ReferenceBook:
    """Readable O(N log N) oracle; it intentionally shares no engine structures."""

    def __init__(
        self, symbol: str, *, stp_policy: SelfTradePolicy = SelfTradePolicy.CANCEL_TAKER
    ) -> None:
        self.symbol = symbol
        self.stp_policy = stp_policy
        self.live: dict[str, ReferenceOrder] = {}
        self.seen: set[str] = set()
        self.trades: list[tuple[str, str, int, int]] = []
        self.priority = 0

    def _opposing(self, side: Side) -> list[ReferenceOrder]:
        orders = [order for order in self.live.values() if order.side is side.opposite]
        return sorted(
            orders,
            key=lambda order: (
                order.price if side is Side.BUY else -int(order.price or 0),
                order.priority,
            ),
        )

    @staticmethod
    def _crosses(order: ReferenceOrder, price: int | None) -> bool:
        if price is None:
            return False
        if order.order_type is OrderType.MARKET:
            return True
        assert order.price is not None
        return price <= order.price if order.side is Side.BUY else price >= order.price

    def _available(self, order: ReferenceOrder) -> int:
        quantity = 0
        for maker in self._opposing(order.side):
            if not self._crosses(order, maker.price):
                break
            if (
                self.stp_policy is SelfTradePolicy.CANCEL_TAKER
                and maker.account_id == order.account_id
            ):
                return quantity
            quantity += maker.remaining
        return quantity

    def process(self, command: Command) -> list[tuple[str, str, int, int]]:
        start = len(self.trades)
        if isinstance(command, NewOrder):
            source = command.order
            if (
                source.symbol != self.symbol
                or not source.order_id
                or source.order_id in self.seen
                or source.quantity <= 0
                or (source.order_type is OrderType.LIMIT and (source.price_ticks or 0) <= 0)
                or (
                    source.order_type is OrderType.MARKET
                    and source.time_in_force not in {TimeInForce.IOC, TimeInForce.FOK}
                )
            ):
                return []
            self.priority += 1
            incoming = ReferenceOrder(
                source.order_id,
                source.account_id,
                source.side,
                source.order_type,
                source.time_in_force,
                source.price_ticks,
                source.quantity,
                source.quantity,
                0,
                self.priority,
            )
            if incoming.tif is TimeInForce.POST_ONLY:
                opposing = self._opposing(incoming.side)
                if opposing and self._crosses(incoming, opposing[0].price):
                    return []
            if incoming.tif is TimeInForce.FOK and self._available(incoming) < incoming.quantity:
                return []
            self.seen.add(incoming.order_id)
            self._match_or_rest(incoming)
        elif isinstance(command, CancelOrder):
            order = self.live.get(command.order_id)
            if order and (command.account_id is None or command.account_id == order.account_id):
                self.live.pop(command.order_id)
        elif isinstance(command, ModifyOrder):
            order = self.live.get(command.order_id)
            if not order or (
                command.account_id is not None and command.account_id != order.account_id
            ):
                return []
            price = order.price if command.new_price_ticks is None else command.new_price_ticks
            if price is None or price <= 0 or command.new_quantity <= order.filled:
                return []
            replacement_remaining = command.new_quantity - order.filled
            loses_priority = price != order.price or command.new_quantity > order.quantity
            if order.tif is TimeInForce.POST_ONLY:
                probe = ReferenceOrder(
                    order.order_id,
                    order.account_id,
                    order.side,
                    order.order_type,
                    order.tif,
                    price,
                    command.new_quantity,
                    replacement_remaining,
                    order.filled,
                    order.priority,
                )
                opposing = self._opposing(order.side)
                if opposing and self._crosses(probe, opposing[0].price):
                    return []
            order.quantity = command.new_quantity
            order.remaining = replacement_remaining
            order.price = price
            if loses_priority:
                self.live.pop(order.order_id)
                self.priority += 1
                order.priority = self.priority
                self._match_or_rest(order)
        return self.trades[start:]

    def _match_or_rest(self, incoming: ReferenceOrder) -> None:
        for maker in self._opposing(incoming.side):
            if incoming.remaining <= 0 or not self._crosses(incoming, maker.price):
                break
            if (
                self.stp_policy is SelfTradePolicy.CANCEL_TAKER
                and maker.account_id == incoming.account_id
            ):
                return
            quantity = min(incoming.remaining, maker.remaining)
            incoming.remaining -= quantity
            incoming.filled += quantity
            maker.remaining -= quantity
            maker.filled += quantity
            self.trades.append((maker.order_id, incoming.order_id, int(maker.price or 0), quantity))
            if maker.remaining == 0:
                self.live.pop(maker.order_id)
        if (
            incoming.remaining
            and incoming.order_type is OrderType.LIMIT
            and incoming.tif
            in {
                TimeInForce.GTC,
                TimeInForce.POST_ONLY,
            }
        ):
            self.live[incoming.order_id] = incoming

    def canonical_live(self) -> list[tuple[str, str, int, int, int]]:
        return sorted(
            (
                order.order_id,
                order.side.value,
                int(order.price or 0),
                order.remaining,
                order.filled,
            )
            for order in self.live.values()
        )

    def canonical_depth(self) -> dict[str, list[tuple[int, int, int]]]:
        levels: dict[tuple[Side, int], list[ReferenceOrder]] = {}
        for order in self.live.values():
            levels.setdefault((order.side, int(order.price or 0)), []).append(order)
        bids = sorted(
            (
                (price, sum(order.remaining for order in orders), len(orders))
                for (side, price), orders in levels.items()
                if side is Side.BUY
            ),
            reverse=True,
        )
        asks = sorted(
            (
                (price, sum(order.remaining for order in orders), len(orders))
                for (side, price), orders in levels.items()
                if side is Side.SELL
            )
        )
        return {"bids": bids, "asks": asks}

    def debug_state(self) -> dict[str, Any]:
        return {
            "live": self.canonical_live(),
            "depth": self.canonical_depth(),
            "trades": self.trades,
        }
