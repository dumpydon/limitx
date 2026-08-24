from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from limitx.domain.commands import Command, NewOrder, command_from_dict
from limitx.domain.enums import EventType
from limitx.engine.order_book import OrderBook
from limitx.replay.journal import EventJournal
from limitx.risk.gateway import RiskGateway


@dataclass(frozen=True, slots=True)
class ReplayResult:
    books: dict[str, OrderBook]
    commands_replayed: int
    divergences: tuple[str, ...]

    @property
    def checksums(self) -> dict[str, str]:
        return {symbol: book.checksum() for symbol, book in self.books.items()}


class ReplaySession:
    def __init__(self, journal: EventJournal) -> None:
        self.journal = journal
        self.position = 0
        self.books: dict[str, OrderBook] = {}
        self.risk = RiskGateway()

    @staticmethod
    def _symbol(command: Command) -> str:
        return command.order.symbol if hasattr(command, "order") else command.symbol

    def reset(self) -> None:
        self.position = 0
        self.books.clear()
        self.risk = RiskGateway()

    def step(self) -> dict[str, Any] | None:
        if self.position >= len(self.journal.entries):
            return None
        entry = self.journal.entries[self.position]
        command = command_from_dict(entry.command)
        symbol = self._symbol(command)
        book = self.books.setdefault(symbol, OrderBook(symbol, audit_mode=True))
        if isinstance(command, NewOrder) and self.journal.risk_enabled:
            decision = self.risk.check(command.order, book)
            if decision.accepted:
                events = book.process(command)
            else:
                if decision.reason is None:
                    raise AssertionError("rejected risk decision must have a reason")
                events = book.reject_by_risk(command.order, decision.reason, decision.detail)
        else:
            events = book.process(command)
        if self.journal.risk_enabled:
            for event in events:
                if event.event_type is EventType.TRADE_EXECUTED:
                    trade = dict(event.data)
                    trade["symbol"] = symbol
                    self.risk.apply_trade(trade)
        self.position += 1
        return {
            "position": self.position,
            "command_sequence": entry.command_sequence,
            "events": [event.as_dict() for event in events],
            "snapshot": book.snapshot(),
        }

    def jump(self, position: int) -> dict[str, OrderBook]:
        if position < 0 or position > len(self.journal.entries):
            raise ValueError("replay position out of range")
        if position < self.position:
            self.reset()
        while self.position < position:
            self.step()
        return self.books

    def run(self, *, compare_events: bool = True) -> ReplayResult:
        divergences: list[str] = []
        while self.position < len(self.journal.entries):
            entry = self.journal.entries[self.position]
            result = self.step()
            assert result is not None
            if compare_events and list(entry.events) != result["events"]:
                divergences.append(f"command {entry.command_sequence}: event output differs")
        for symbol, expected in self.journal.final_checksums.items():
            actual = self.books[symbol].checksum() if symbol in self.books else "missing"
            if actual != expected:
                divergences.append(f"{symbol}: checksum expected {expected}, got {actual}")
        return ReplayResult(self.books, self.position, tuple(divergences))
