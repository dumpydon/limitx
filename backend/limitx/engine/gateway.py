from __future__ import annotations

import asyncio
import contextlib
import json
import resource
from dataclasses import dataclass
from typing import Any

from limitx.analytics.ledger import AccountLedger
from limitx.analytics.microstructure import calculate_metrics
from limitx.analytics.surveillance import SurveillanceEngine
from limitx.domain.commands import Command, NewOrder
from limitx.domain.enums import EventType, OrderType, Side, TimeInForce
from limitx.domain.order import Order
from limitx.engine.events import EngineEvent
from limitx.engine.order_book import OrderBook
from limitx.market_data.projector import EventBroker, MarketDataProjector
from limitx.replay.journal import EventJournal
from limitx.risk.gateway import RiskGateway


@dataclass(slots=True)
class WorkItem:
    command: Command
    future: asyncio.Future[list[EngineEvent]]


class SymbolWorker:
    """One queue and one mutation task: the single writer for one symbol."""

    def __init__(self, symbol: str, handler: Any, *, capacity: int = 10_000) -> None:
        self.symbol = symbol
        self.handler = handler
        self.capacity = capacity
        self.queue: asyncio.Queue[WorkItem] = asyncio.Queue(capacity)
        self.task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self.task is None or self.task.done():
            # Lifespan-based test servers may restart the app on a new event loop.
            self.queue = asyncio.Queue(self.capacity)
            self.task = asyncio.create_task(self._run(), name=f"limitx-{self.symbol}")

    async def stop(self) -> None:
        if self.task is not None:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task
            self.task = None

    async def submit(self, command: Command) -> list[EngineEvent]:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[list[EngineEvent]] = loop.create_future()
        await self.queue.put(WorkItem(command, future))
        return await future

    async def _run(self) -> None:
        while True:
            item = await self.queue.get()
            try:
                item.future.set_result(self.handler(item.command))
            except Exception as error:
                item.future.set_exception(error)
            finally:
                self.queue.task_done()


class EngineGateway:
    SYMBOLS = ("BTC-USD", "ETH-USD", "AAPL", "MSFT")

    def __init__(self) -> None:
        self.books = {symbol: OrderBook(symbol) for symbol in self.SYMBOLS}
        self.projectors = {symbol: MarketDataProjector(book) for symbol, book in self.books.items()}
        self.journals = {
            symbol: EventJournal(f"live-{symbol}", risk_enabled=True) for symbol in self.SYMBOLS
        }
        self.risk = RiskGateway()
        self.ledger = AccountLedger()
        self.surveillance = SurveillanceEngine()
        self.broker = EventBroker()
        self.alerts: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in self.SYMBOLS}
        self.workers = {
            symbol: SymbolWorker(symbol, lambda command, s=symbol: self.process_direct(s, command))
            for symbol in self.SYMBOLS
        }

    def start(self) -> None:
        for worker in self.workers.values():
            worker.start()

    async def stop(self) -> None:
        await asyncio.gather(*(worker.stop() for worker in self.workers.values()))

    @staticmethod
    def command_symbol(command: Command) -> str:
        return command.order.symbol if isinstance(command, NewOrder) else command.symbol

    async def process(self, command: Command) -> list[EngineEvent]:
        symbol = self.command_symbol(command)
        if symbol not in self.workers:
            raise ValueError("unsupported symbol")
        return await self.workers[symbol].submit(command)

    def process_direct(self, symbol: str, command: Command) -> list[EngineEvent]:
        book = self.books[symbol]
        if isinstance(command, NewOrder):
            decision = self.risk.check(command.order, book)
            if decision.accepted:
                events = book.process(command)
            else:
                if decision.reason is None:
                    raise AssertionError("rejected risk decision must have a reason")
                events = book.reject_by_risk(command.order, decision.reason, decision.detail)
        else:
            events = book.process(command)
        self.journals[symbol].record(command, events)
        for event in events:
            if event.event_type is EventType.TRADE_EXECUTED:
                trade = dict(event.data)
                self.ledger.apply_trade(symbol, trade)
                trade["symbol"] = symbol
                self.risk.apply_trade(trade)
        messages = self.projectors[symbol].project(events)
        snapshot = self.projectors[symbol].snapshot()
        for message in messages:
            self.broker.publish(symbol, message, snapshot)
        self.alerts[symbol] = [alert.as_dict() for alert in self.surveillance.scan(book.events)][
            -20:
        ]
        return events

    def reset(self, symbol: str) -> None:
        self.books[symbol] = OrderBook(symbol)
        self.projectors[symbol] = MarketDataProjector(self.books[symbol])
        self.journals[symbol] = EventJournal(f"live-{symbol}", risk_enabled=True)
        self.alerts[symbol] = []
        self.risk.state.positions = {
            key: value for key, value in self.risk.state.positions.items() if key[1] != symbol
        }
        self.ledger.positions = {
            key: value for key, value in self.ledger.positions.items() if key[1] != symbol
        }

    def seed(self, symbol: str, center_ticks: int = 10_000_000, levels: int = 12) -> None:
        for offset in range(levels, 0, -1):
            for side in (Side.BUY, Side.SELL):
                order = Order(
                    order_id=f"SEED-{symbol}-{side.value}-{offset}",
                    symbol=symbol,
                    account_id=f"seed-{side.value.lower()}-{offset}",
                    side=side,
                    order_type=OrderType.LIMIT,
                    time_in_force=TimeInForce.GTC,
                    price_ticks=center_ticks - offset
                    if side is Side.BUY
                    else center_ticks + offset,
                    quantity=35 + (levels - offset) * 5,
                )
                self.process_direct(symbol, NewOrder(order))

    def system_state(self, symbol: str) -> dict[str, Any]:
        book = self.books[symbol]
        snapshot_size = len(json.dumps(book.snapshot(), separators=(",", ":")).encode())
        return {
            "engine_sequence": book.sequencer.value,
            "active_orders": len(book.live_orders),
            "bid_levels": len(book.bids),
            "ask_levels": len(book.asks),
            "event_journal_size": len(self.journals[symbol].entries),
            "connected_clients": self.broker.connected_clients,
            "queue_depth": self.workers[symbol].queue.qsize(),
            "snapshot_sequence": book.sequencer.value,
            "last_checksum": book.checksum(),
            "snapshot_size_bytes": snapshot_size,
            "process_max_rss_platform_units": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "metrics": calculate_metrics(book),
        }
