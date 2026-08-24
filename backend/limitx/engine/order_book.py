from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from limitx.domain.commands import CancelOrder, Command, NewOrder
from limitx.domain.enums import (
    EventType,
    OrderStatus,
    OrderType,
    RejectReason,
    SelfTradePolicy,
    Side,
    TimeInForce,
)
from limitx.domain.order import Order
from limitx.engine.events import EngineEvent
from limitx.engine.linked_orders import OrderNode
from limitx.engine.price_index import PriceIndex
from limitx.engine.sequencer import Sequencer


class OrderBook:
    """Pure, deterministic price-time-priority book for one symbol.

    It intentionally has no knowledge of HTTP, asyncio, WebSockets, or wall-clock time.
    Logical time is derived from the strictly increasing event sequence.
    """

    def __init__(
        self,
        symbol: str,
        *,
        tick_size: str = "0.01",
        stp_policy: SelfTradePolicy = SelfTradePolicy.CANCEL_TAKER,
        audit_mode: bool = False,
    ) -> None:
        self.symbol = symbol
        self.tick_size = tick_size
        self.stp_policy = stp_policy
        self.audit_mode = audit_mode
        self.bids = PriceIndex(Side.BUY)
        self.asks = PriceIndex(Side.SELL)
        self.live_orders: dict[str, OrderNode] = {}
        self.orders: dict[str, Order] = {}
        self.trades: list[dict[str, Any]] = []
        self.events: list[EngineEvent] = []
        self.sequencer = Sequencer()

    @property
    def best_bid(self) -> int | None:
        level = self.bids.best
        return level.price if level else None

    @property
    def best_ask(self) -> int | None:
        level = self.asks.best
        return level.price if level else None

    def process(self, command: Command) -> list[EngineEvent]:
        if isinstance(command, NewOrder):
            result = self.submit(command.order)
        elif isinstance(command, CancelOrder):
            result = self.cancel(command.order_id, command.account_id)
        else:
            result = self.modify(
                command.order_id,
                command.new_quantity,
                command.new_price_ticks,
                command.account_id,
            )
        if self.audit_mode:
            self.assert_invariants()
        return result

    def _emit(
        self,
        event_type: EventType,
        *,
        order_id: str | None = None,
        **data: Any,
    ) -> EngineEvent:
        sequence = self.sequencer.next()
        event = EngineEvent(
            sequence=sequence,
            event_type=event_type,
            symbol=self.symbol,
            order_id=order_id,
            logical_time_ns=sequence * 1_000,
            data=data,
        )
        self.events.append(event)
        return event

    def _reject(
        self,
        order: Order,
        reason: RejectReason,
        *,
        kind: EventType = EventType.ORDER_REJECTED,
    ) -> list[EngineEvent]:
        order.status = OrderStatus.REJECTED
        event = self._emit(kind, order_id=order.order_id, reason=reason.value)
        return [event]

    def _validation_reason(self, order: Order) -> RejectReason | None:
        if order.symbol != self.symbol:
            return RejectReason.INVALID_MODIFICATION
        if not order.order_id or order.order_id in self.orders:
            return RejectReason.DUPLICATE_ORDER_ID
        if order.quantity <= 0:
            return RejectReason.INVALID_QUANTITY
        if order.order_type is OrderType.LIMIT and (
            order.price_ticks is None or order.price_ticks <= 0
        ):
            return RejectReason.INVALID_PRICE
        if order.order_type is OrderType.MARKET and order.time_in_force not in {
            TimeInForce.IOC,
            TimeInForce.FOK,
        }:
            return RejectReason.MARKET_REQUIRES_IOC_OR_FOK
        return None

    def _crosses(self, order: Order, best_price: int | None = None) -> bool:
        price = best_price
        if price is None:
            price = self.best_ask if order.side is Side.BUY else self.best_bid
        if price is None:
            return False
        if order.order_type is OrderType.MARKET:
            return True
        assert order.price_ticks is not None
        return price <= order.price_ticks if order.side is Side.BUY else price >= order.price_ticks

    def _available_liquidity(self, order: Order) -> int:
        index = self.asks if order.side is Side.BUY else self.bids
        available = 0
        for level in index.levels_best_first():
            if not self._crosses(order, level.price):
                break
            node = level.head
            while node is not None:
                if (
                    self.stp_policy is SelfTradePolicy.CANCEL_TAKER
                    and node.order.account_id == order.account_id
                ):
                    return available
                available += node.order.remaining_qty
                if available >= order.quantity:
                    return available
                node = node.next
        return available

    def submit(self, order: Order) -> list[EngineEvent]:
        reason = self._validation_reason(order)
        if reason:
            return self._reject(order, reason)
        if order.time_in_force is TimeInForce.POST_ONLY and self._crosses(order):
            return self._reject(order, RejectReason.POST_ONLY_WOULD_TRADE)
        if (
            order.time_in_force is TimeInForce.FOK
            and self._available_liquidity(order) < order.quantity
        ):
            return self._reject(order, RejectReason.FOK_NOT_FILLABLE)

        self.orders[order.order_id] = order
        accepted = self._emit(
            EventType.ORDER_ACCEPTED,
            order_id=order.order_id,
            account_id=order.account_id,
            side=order.side.value,
            order_type=order.order_type.value,
            time_in_force=order.time_in_force.value,
            price_ticks=order.price_ticks,
            quantity=order.quantity,
        )
        order.status = OrderStatus.ACCEPTED
        order.accepted_sequence = accepted.sequence
        order.created_at_ns = accepted.logical_time_ns
        emitted = [accepted]
        arrival_mid_ticks_x2 = (
            self.best_bid + self.best_ask
            if self.best_bid is not None and self.best_ask is not None
            else None
        )
        self._execute_accepted(order, emitted, arrival_mid_ticks_x2)
        self._finish_book_update(emitted)
        return emitted

    def reject_by_risk(self, order: Order, reason: RejectReason, detail: str) -> list[EngineEvent]:
        """Sequence a gateway rejection without allowing the order into matcher state."""
        if order.order_id in self.orders:
            return self._reject(order, RejectReason.DUPLICATE_ORDER_ID)
        order.status = OrderStatus.REJECTED
        self.orders[order.order_id] = order
        event = self._emit(
            EventType.RISK_REJECTED,
            order_id=order.order_id,
            reason=reason.value,
            detail=detail,
        )
        return [event]

    def _execute_accepted(
        self,
        incoming: Order,
        emitted: list[EngineEvent],
        arrival_mid_ticks_x2: int | None = None,
    ) -> None:
        opposing = self.asks if incoming.side is Side.BUY else self.bids
        while incoming.remaining_qty > 0:
            level = opposing.best
            if level is None or not self._crosses(incoming, level.price):
                break
            maker_node = level.head
            if maker_node is None:
                raise AssertionError("indexed price level has no head")
            maker = maker_node.order
            if (
                self.stp_policy is SelfTradePolicy.CANCEL_TAKER
                and maker.account_id == incoming.account_id
            ):
                incoming.status = OrderStatus.CANCELLED
                emitted.append(
                    self._emit(
                        EventType.ORDER_CANCELLED,
                        order_id=incoming.order_id,
                        reason=RejectReason.SELF_TRADE_PREVENTION.value,
                        remaining_qty=incoming.remaining_qty,
                    )
                )
                return

            trade_qty = min(incoming.remaining_qty, maker.remaining_qty)
            level.consume(maker_node, trade_qty)
            maker.remaining_qty -= trade_qty
            maker.filled_qty += trade_qty
            incoming.remaining_qty -= trade_qty
            incoming.filled_qty += trade_qty
            trade = {
                "trade_id": f"T{self.sequencer.value + 1:012d}",
                "maker_order_id": maker.order_id,
                "taker_order_id": incoming.order_id,
                "maker_account_id": maker.account_id,
                "taker_account_id": incoming.account_id,
                "price_ticks": level.price,
                "quantity": trade_qty,
                "aggressor_side": incoming.side.value,
                "arrival_mid_ticks_x2": arrival_mid_ticks_x2,
                "slippage_ticks_x2": (
                    (1 if incoming.side is Side.BUY else -1)
                    * (2 * level.price - arrival_mid_ticks_x2)
                    if arrival_mid_ticks_x2 is not None
                    else None
                ),
            }
            trade_event = self._emit(
                EventType.TRADE_EXECUTED,
                order_id=incoming.order_id,
                **trade,
            )
            trade["sequence"] = trade_event.sequence
            trade["logical_time_ns"] = trade_event.logical_time_ns
            self.trades.append(trade)
            emitted.append(trade_event)

            maker_event = (
                EventType.ORDER_FILLED
                if maker.remaining_qty == 0
                else EventType.ORDER_PARTIALLY_FILLED
            )
            maker.status = (
                OrderStatus.FILLED if maker.remaining_qty == 0 else OrderStatus.PARTIALLY_FILLED
            )
            emitted.append(
                self._emit(
                    maker_event,
                    order_id=maker.order_id,
                    fill_quantity=trade_qty,
                    filled_qty=maker.filled_qty,
                    remaining_qty=maker.remaining_qty,
                    trade_sequence=trade_event.sequence,
                )
            )
            if maker.remaining_qty == 0:
                level.remove(maker_node)
                self.live_orders.pop(maker.order_id, None)
                if level.is_empty:
                    opposing.remove(level.price)

            incoming_event = (
                EventType.ORDER_FILLED
                if incoming.remaining_qty == 0
                else EventType.ORDER_PARTIALLY_FILLED
            )
            incoming.status = (
                OrderStatus.FILLED if incoming.remaining_qty == 0 else OrderStatus.PARTIALLY_FILLED
            )
            emitted.append(
                self._emit(
                    incoming_event,
                    order_id=incoming.order_id,
                    fill_quantity=trade_qty,
                    filled_qty=incoming.filled_qty,
                    remaining_qty=incoming.remaining_qty,
                    trade_sequence=trade_event.sequence,
                )
            )

        if incoming.remaining_qty == 0 or incoming.status is OrderStatus.CANCELLED:
            return
        should_cancel = incoming.order_type is OrderType.MARKET or incoming.time_in_force in {
            TimeInForce.IOC,
            TimeInForce.FOK,
        }
        if should_cancel:
            incoming.status = OrderStatus.CANCELLED
            emitted.append(
                self._emit(
                    EventType.ORDER_CANCELLED,
                    order_id=incoming.order_id,
                    reason="UNFILLED_REMAINDER",
                    remaining_qty=incoming.remaining_qty,
                )
            )
            return
        self._rest(incoming)

    def _rest(self, order: Order) -> None:
        if order.price_ticks is None:
            raise AssertionError("market order cannot rest")
        index = self.bids if order.side is Side.BUY else self.asks
        node = OrderNode(order)
        index.get_or_create(order.price_ticks).append(node)
        self.live_orders[order.order_id] = node

    def _finish_book_update(self, emitted: list[EngineEvent]) -> None:
        emitted.append(
            self._emit(
                EventType.BOOK_UPDATED,
                best_bid=self.best_bid,
                best_ask=self.best_ask,
                live_orders=len(self.live_orders),
            )
        )

    def cancel(self, order_id: str, account_id: str | None = None) -> list[EngineEvent]:
        node = self.live_orders.get(order_id)
        if node is None or (account_id is not None and node.order.account_id != account_id):
            event = self._emit(
                EventType.CANCEL_REJECTED,
                order_id=order_id,
                reason=RejectReason.UNKNOWN_ORDER.value,
            )
            return [event]
        order = node.order
        level = node.level
        if level is None:
            raise AssertionError("live order is detached")
        index = self.bids if order.side is Side.BUY else self.asks
        level.remove(node)
        if level.is_empty:
            index.remove(level.price)
        self.live_orders.pop(order_id)
        order.status = OrderStatus.CANCELLED
        emitted = [
            self._emit(
                EventType.ORDER_CANCELLED,
                order_id=order_id,
                reason="USER_REQUEST",
                remaining_qty=order.remaining_qty,
            )
        ]
        self._finish_book_update(emitted)
        return emitted

    def modify(
        self,
        order_id: str,
        new_quantity: int,
        new_price_ticks: int | None = None,
        account_id: str | None = None,
    ) -> list[EngineEvent]:
        node = self.live_orders.get(order_id)
        if node is None or (account_id is not None and node.order.account_id != account_id):
            return [
                self._emit(
                    EventType.MODIFY_REJECTED,
                    order_id=order_id,
                    reason=RejectReason.UNKNOWN_ORDER.value,
                )
            ]
        order = node.order
        price = order.price_ticks if new_price_ticks is None else new_price_ticks
        if price is None or price <= 0 or new_quantity <= order.filled_qty:
            return [
                self._emit(
                    EventType.MODIFY_REJECTED,
                    order_id=order_id,
                    reason=RejectReason.INVALID_MODIFICATION.value,
                )
            ]
        replacement_remaining = new_quantity - order.filled_qty
        loses_priority = price != order.price_ticks or new_quantity > order.quantity
        if order.time_in_force is TimeInForce.POST_ONLY:
            probe = Order(
                order_id=order.order_id,
                symbol=order.symbol,
                account_id=order.account_id,
                side=order.side,
                order_type=order.order_type,
                quantity=replacement_remaining,
                price_ticks=price,
                time_in_force=order.time_in_force,
            )
            if self._crosses(probe):
                return [
                    self._emit(
                        EventType.MODIFY_REJECTED,
                        order_id=order_id,
                        reason=RejectReason.POST_ONLY_WOULD_TRADE.value,
                    )
                ]

        old_price = order.price_ticks
        old_quantity = order.quantity
        emitted: list[EngineEvent] = []
        if not loses_priority:
            level = node.level
            if level is None:
                raise AssertionError("live order is detached")
            level.total_quantity += replacement_remaining - order.remaining_qty
            order.quantity = new_quantity
            order.remaining_qty = replacement_remaining
            emitted.append(
                self._emit(
                    EventType.ORDER_MODIFIED,
                    order_id=order_id,
                    old_price_ticks=old_price,
                    new_price_ticks=price,
                    old_quantity=old_quantity,
                    new_quantity=new_quantity,
                    priority_retained=True,
                )
            )
            self._finish_book_update(emitted)
            return emitted

        level = node.level
        if level is None:
            raise AssertionError("live order is detached")
        index = self.bids if order.side is Side.BUY else self.asks
        level.remove(node)
        if level.is_empty:
            index.remove(level.price)
        self.live_orders.pop(order_id)
        arrival_mid_ticks_x2 = (
            self.best_bid + self.best_ask
            if self.best_bid is not None and self.best_ask is not None
            else None
        )
        order.price_ticks = price
        order.quantity = new_quantity
        order.remaining_qty = replacement_remaining
        modified = self._emit(
            EventType.ORDER_MODIFIED,
            order_id=order_id,
            old_price_ticks=old_price,
            new_price_ticks=price,
            old_quantity=old_quantity,
            new_quantity=new_quantity,
            priority_retained=False,
        )
        emitted.append(modified)
        order.accepted_sequence = modified.sequence
        order.status = OrderStatus.PARTIALLY_FILLED if order.filled_qty else OrderStatus.ACCEPTED
        self._execute_accepted(order, emitted, arrival_mid_ticks_x2)
        self._finish_book_update(emitted)
        return emitted

    def depth(self, levels: int | None = None) -> dict[str, list[dict[str, int]]]:
        def collect(index: PriceIndex) -> list[dict[str, int]]:
            result = [
                {
                    "price_ticks": level.price,
                    "quantity": level.total_quantity,
                    "order_count": level.order_count,
                }
                for level in index.levels_best_first()
            ]
            return result[:levels] if levels is not None else result

        return {"bids": collect(self.bids), "asks": collect(self.asks)}

    def canonical_state(self) -> dict[str, object]:
        def orders(index: PriceIndex) -> list[dict[str, object]]:
            return [
                {
                    "price_ticks": level.price,
                    "orders": [
                        {
                            "order_id": node.order.order_id,
                            "account_id": node.order.account_id,
                            "quantity": node.order.quantity,
                            "remaining_qty": node.order.remaining_qty,
                            "filled_qty": node.order.filled_qty,
                            "priority": node.order.accepted_sequence,
                        }
                        for node in level
                    ],
                }
                for level in index.levels_best_first()
            ]

        return {
            "symbol": self.symbol,
            "sequence": self.sequencer.value,
            "bids": orders(self.bids),
            "asks": orders(self.asks),
        }

    def checksum(self) -> str:
        payload = json.dumps(self.canonical_state(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def snapshot(self) -> dict[str, object]:
        state = self.canonical_state()
        state.update(
            {
                "tick_size": self.tick_size,
                "live_order_count": len(self.live_orders),
                "depth": self.depth(),
                "checksum": self.checksum(),
            }
        )
        return state

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, Any], *, audit_mode: bool = False) -> OrderBook:
        book = cls(
            str(snapshot["symbol"]),
            tick_size=str(snapshot.get("tick_size", "0.01")),
            audit_mode=audit_mode,
        )
        for side_name in ("bids", "asks"):
            side = Side.BUY if side_name == "bids" else Side.SELL
            for level_data in snapshot.get(side_name, []):
                price = int(level_data["price_ticks"])
                for item in level_data["orders"]:
                    filled = int(item.get("filled_qty", 0))
                    remaining = int(item["remaining_qty"])
                    order = Order(
                        order_id=str(item["order_id"]),
                        symbol=book.symbol,
                        account_id=str(item.get("account_id", "snapshot")),
                        side=side,
                        order_type=OrderType.LIMIT,
                        time_in_force=TimeInForce.GTC,
                        price_ticks=price,
                        quantity=int(item.get("quantity", filled + remaining)),
                        remaining_qty=remaining,
                        filled_qty=filled,
                        status=(OrderStatus.PARTIALLY_FILLED if filled else OrderStatus.ACCEPTED),
                        accepted_sequence=int(item["priority"]),
                    )
                    book.orders[order.order_id] = order
                    book._rest(order)
        book.sequencer.value = int(snapshot["sequence"])
        if snapshot.get("checksum") and book.checksum() != snapshot["checksum"]:
            raise ValueError("snapshot checksum mismatch")
        book.assert_invariants()
        return book

    def assert_invariants(self) -> None:
        if self.best_bid is not None and self.best_ask is not None:
            assert self.best_bid < self.best_ask, "resting book is crossed"
        seen: set[str] = set()
        for index in (self.bids, self.asks):
            for level in index.levels_best_first():
                assert not level.is_empty, "empty price level retained"
                total = 0
                count = 0
                previous_priority = -1
                previous_node: OrderNode | None = None
                for node in level:
                    order = node.order
                    assert node.level is level
                    assert node.previous is previous_node
                    assert order.order_id not in seen, "live order appears twice"
                    assert order.remaining_qty > 0
                    assert order.remaining_qty <= order.quantity
                    assert order.filled_qty + order.remaining_qty == order.quantity
                    assert order.status in {OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}
                    assert order.accepted_sequence >= previous_priority, "FIFO priority violated"
                    assert self.live_orders.get(order.order_id) is node
                    assert order.price_ticks == level.price
                    seen.add(order.order_id)
                    total += order.remaining_qty
                    count += 1
                    previous_priority = order.accepted_sequence
                    previous_node = node
                assert previous_node is level.tail
                assert total == level.total_quantity
                assert count == level.order_count
        assert seen == set(self.live_orders)
        for order in self.orders.values():
            assert order.filled_qty >= 0
            assert 0 <= order.remaining_qty <= order.quantity
            assert order.filled_qty + order.remaining_qty == order.quantity
            if order.status in {OrderStatus.CANCELLED, OrderStatus.FILLED, OrderStatus.REJECTED}:
                assert order.order_id not in self.live_orders
        assert all(int(trade["quantity"]) > 0 for trade in self.trades)
        assert all(
            a.sequence < b.sequence for a, b in zip(self.events, self.events[1:], strict=False)
        )

    def iter_live_orders(self, account_id: str | None = None) -> Iterable[Order]:
        for node in self.live_orders.values():
            if account_id is None or node.order.account_id == account_id:
                yield node.order
