from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from limitx.domain.commands import NewOrder, command_from_dict
from limitx.domain.enums import EventType
from limitx.engine.order_book import OrderBook
from limitx.replay.journal import EventJournal
from limitx.risk.gateway import RiskGateway, RiskLimits


@dataclass(frozen=True, slots=True)
class RecoveryPoint:
    snapshot: dict[str, Any]
    journal_position: int
    risk_positions: dict[tuple[str, str], int]


def create_recovery_point(
    book: OrderBook,
    journal: EventJournal,
    risk: RiskGateway,
) -> RecoveryPoint:
    return RecoveryPoint(
        snapshot=book.snapshot(),
        journal_position=len(journal.entries),
        risk_positions=dict(risk.state.positions),
    )


def recover(
    point: RecoveryPoint,
    journal: EventJournal,
    limits: RiskLimits,
    expected_book: OrderBook,
) -> dict[str, Any]:
    recovered = OrderBook.from_snapshot(point.snapshot, audit_mode=True)
    risk = RiskGateway(limits)
    risk.state.positions = dict(point.risk_positions)
    divergences: list[str] = []
    event_count = 0
    for entry in journal.entries[point.journal_position :]:
        command = command_from_dict(entry.command)
        if isinstance(command, NewOrder) and journal.risk_enabled:
            decision = risk.check(command.order, recovered)
            if decision.accepted:
                events = recovered.process(command)
            else:
                if decision.reason is None:
                    raise AssertionError("risk rejection has no reason")
                events = recovered.reject_by_risk(
                    command.order,
                    decision.reason,
                    decision.detail,
                    observed=decision.observed,
                    threshold=decision.threshold,
                )
        else:
            events = recovered.process(command)
        event_count += len(events)
        if [event.as_dict() for event in events] != list(entry.events):
            divergences.append(f"command {entry.command_sequence}: event divergence")
        for event in events:
            if event.event_type is EventType.TRADE_EXECUTED:
                trade = dict(event.data)
                trade["symbol"] = recovered.symbol
                risk.apply_trade(trade)
    recovered.assert_invariants()
    expected_checksum = expected_book.checksum()
    recovered_checksum = recovered.checksum()
    if expected_checksum != recovered_checksum:
        divergences.append("final checksum mismatch")
    return {
        "snapshot_sequence": int(point.snapshot["sequence"]),
        "snapshot_checksum": point.snapshot["checksum"],
        "commands_replayed": len(journal.entries) - point.journal_position,
        "events_replayed": event_count,
        "final_sequence": recovered.sequencer.value,
        "expected_checksum": expected_checksum,
        "recovered_checksum": recovered_checksum,
        "divergences": divergences,
        "status": "PASS" if not divergences else "FAIL",
    }
