from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Any

from limitx.domain.enums import EventType
from limitx.engine.events import EngineEvent
from limitx.engine.order_book import OrderBook
from limitx.market_data.checksum import depth_checksum


@dataclass(slots=True)
class SequenceGuard:
    expected: int | None = None
    synchronized: bool = False

    def accept_snapshot(self, sequence: int) -> None:
        self.expected = sequence + 1
        self.synchronized = True

    def accept_delta(self, sequence: int) -> str:
        if not self.synchronized or self.expected is None:
            return "RESYNC_REQUIRED"
        if sequence < self.expected:
            return "DUPLICATE_OR_OLD"
        if sequence > self.expected:
            self.synchronized = False
            return "GAP"
        self.expected += 1
        return "APPLIED"


class MarketDataProjector:
    def __init__(self, book: OrderBook, *, depth_levels: int = 16) -> None:
        self.book = book
        self.depth_levels = depth_levels
        self.recent_trades: deque[dict[str, Any]] = deque(maxlen=80)
        self.volume = 0
        self.notional_ticks = 0
        self.last_depth_sequence = book.sequencer.value

    def _l1(self) -> dict[str, int | None]:
        bid, ask = self.book.best_bid, self.book.best_ask
        return {
            "best_bid": bid,
            "best_ask": ask,
            "spread_ticks": ask - bid if bid is not None and ask is not None else None,
            "mid_ticks_x2": bid + ask if bid is not None and ask is not None else None,
        }

    def snapshot(self) -> dict[str, Any]:
        depth = self.book.depth(self.depth_levels)
        return {
            "type": "book_snapshot",
            "sequence": self.last_depth_sequence,
            "symbol": self.book.symbol,
            "payload": {
                "l1": self._l1(),
                "depth": depth,
                "recent_trades": list(self.recent_trades),
                "volume": self.volume,
                "vwap_ticks": self.notional_ticks / self.volume if self.volume else None,
                "checksum": depth_checksum(self.book.symbol, depth),
            },
        }

    def project(self, events: list[EngineEvent]) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        for event in events:
            if event.event_type is EventType.TRADE_EXECUTED:
                trade = event.as_dict()
                self.recent_trades.appendleft(trade)
                quantity = int(event.data["quantity"])
                self.volume += quantity
                self.notional_ticks += int(event.data["price_ticks"]) * quantity
                messages.append(
                    {
                        "type": "trade",
                        "sequence": event.sequence,
                        "symbol": self.book.symbol,
                        "payload": trade,
                    }
                )
            elif event.event_type is EventType.BOOK_UPDATED:
                depth = self.book.depth(self.depth_levels)
                messages.append(
                    {
                        "type": "book_delta",
                        "sequence": event.sequence,
                        "symbol": self.book.symbol,
                        "payload": {
                            "previous_sequence": self.last_depth_sequence,
                            "l1": self._l1(),
                            "depth": depth,
                            "checksum": depth_checksum(self.book.symbol, depth),
                        },
                    }
                )
                self.last_depth_sequence = event.sequence
        return messages


class EventBroker:
    """Bounded fan-out. Lagging consumers receive a fresh snapshot marker."""

    def __init__(self, *, subscriber_capacity: int = 128) -> None:
        self.subscriber_capacity = subscriber_capacity
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}

    def subscribe(self, symbol: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(self.subscriber_capacity)
        self._subscribers.setdefault(symbol, set()).add(queue)
        return queue

    def unsubscribe(self, symbol: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        subscribers = self._subscribers.get(symbol)
        if subscribers:
            subscribers.discard(queue)

    def publish(self, symbol: str, message: dict[str, Any], snapshot: dict[str, Any]) -> None:
        for queue in tuple(self._subscribers.get(symbol, ())):
            if queue.full():
                while not queue.empty():
                    queue.get_nowait()
                queue.put_nowait(snapshot)
            else:
                queue.put_nowait(message)

    @property
    def connected_clients(self) -> int:
        return sum(len(clients) for clients in self._subscribers.values())
