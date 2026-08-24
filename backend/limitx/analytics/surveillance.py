from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from limitx.domain.enums import EventType
from limitx.engine.events import EngineEvent


@dataclass(frozen=True, slots=True)
class SurveillanceAlert:
    alert_id: str
    participant: str
    rule: str
    explanation: str
    evidence_ids: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "participant": self.participant,
            "rule": self.rule,
            "explanation": self.explanation,
            "evidence_ids": list(self.evidence_ids),
            "classification": "heuristic alert, not proof of manipulation",
        }


class SurveillanceEngine:
    """Explainable sequence-window heuristics above, never inside, matching."""

    def scan(self, events: list[EngineEvent], *, window: int = 500) -> list[SurveillanceAlert]:
        recent = events[-window:]
        accepted: dict[str, list[EngineEvent]] = defaultdict(list)
        cancelled: dict[str, list[EngineEvent]] = defaultdict(list)
        modified: dict[str, list[EngineEvent]] = defaultdict(list)
        account_by_order: dict[str, str] = {}
        cancel_by_order: dict[str, EngineEvent] = {}
        for event in recent:
            if event.event_type is EventType.ORDER_ACCEPTED and event.order_id:
                account = str(event.data.get("account_id", "unknown"))
                account_by_order[event.order_id] = account
                accepted[account].append(event)
            elif event.event_type is EventType.ORDER_CANCELLED and event.order_id:
                account = account_by_order.get(event.order_id, "unknown")
                cancelled[account].append(event)
                cancel_by_order[event.order_id] = event
            elif event.event_type is EventType.ORDER_MODIFIED and event.order_id:
                account = account_by_order.get(event.order_id, "unknown")
                modified[account].append(event)
        alerts: list[SurveillanceAlert] = []
        for account, adds in accepted.items():
            cancels = cancelled[account]
            ratio = len(cancels) / len(adds) if adds else 0
            if len(adds) >= 12 and ratio >= 0.8:
                evidence = tuple(event.evidence_id for event in (adds[-3:] + cancels[-3:]))
                alerts.append(
                    SurveillanceAlert(
                        alert_id=f"alert:cancel-ratio:{account}:{recent[-1].sequence}",
                        participant=account,
                        rule="HIGH_CANCEL_RATIO",
                        explanation=(
                            f"{len(cancels)} cancellations followed {len(adds)} accepted orders "
                            f"inside the last {window} events ({ratio:.0%} ratio)."
                        ),
                        evidence_ids=evidence,
                    )
                )
            replacements = modified[account]
            if len(replacements) >= 10:
                alerts.append(
                    SurveillanceAlert(
                        alert_id=f"alert:replacement:{account}:{recent[-1].sequence}",
                        participant=account,
                        rule="RAPID_REPLACEMENT",
                        explanation=(
                            f"{len(replacements)} order modifications occurred in the window."
                        ),
                        evidence_ids=tuple(event.evidence_id for event in replacements[-6:]),
                    )
                )
            large_quick_cancels = [
                add
                for add in adds
                if add.order_id
                and add.data.get("order_type") == "LIMIT"
                and int(add.data.get("quantity", 0)) >= 100
                and add.order_id in cancel_by_order
                and cancel_by_order[add.order_id].logical_time_ns - add.logical_time_ns <= 100_000
            ]
            if len(large_quick_cancels) >= 6:
                alerts.append(
                    SurveillanceAlert(
                        alert_id=f"alert:spoofing-like:{account}:{recent[-1].sequence}",
                        participant=account,
                        rule="SPOOFING_LIKE_QUICK_CANCEL",
                        explanation=(
                            f"{len(large_quick_cancels)} limit orders of at least 100 units "
                            "were cancelled within 100 logical microseconds."
                        ),
                        evidence_ids=tuple(event.evidence_id for event in large_quick_cancels[-6:]),
                    )
                )
            limit_adds = [event for event in adds if event.data.get("order_type") == "LIMIT"]
            distinct_prices = {event.data.get("price_ticks") for event in limit_adds}
            if len(limit_adds) >= 10 and len(distinct_prices) >= 3 and ratio >= 0.7:
                alerts.append(
                    SurveillanceAlert(
                        alert_id=f"alert:layering-like:{account}:{recent[-1].sequence}",
                        participant=account,
                        rule="LAYERING_LIKE_BURST",
                        explanation=(
                            f"{len(limit_adds)} limit orders spanned {len(distinct_prices)} prices "
                            f"with a {ratio:.0%} cancellation ratio in the event window."
                        ),
                        evidence_ids=tuple(event.evidence_id for event in limit_adds[-6:]),
                    )
                )
        trades_by_taker: dict[str, list[EngineEvent]] = defaultdict(list)
        for event in recent:
            if event.event_type is EventType.TRADE_EXECUTED:
                trades_by_taker[str(event.data.get("taker_order_id"))].append(event)
        for taker_order_id, trade_events in trades_by_taker.items():
            total_quantity = sum(int(event.data["quantity"]) for event in trade_events)
            distinct_levels = {int(event.data["price_ticks"]) for event in trade_events}
            if len(distinct_levels) >= 3 and total_quantity >= 150:
                participant = str(trade_events[0].data.get("taker_account_id", "unknown"))
                alerts.append(
                    SurveillanceAlert(
                        alert_id=f"alert:large-sweep:{taker_order_id}:{recent[-1].sequence}",
                        participant=participant,
                        rule="LARGE_SWEEP",
                        explanation=(
                            f"Aggressive order {taker_order_id} executed {total_quantity} units "
                            f"across {len(distinct_levels)} resting price levels."
                        ),
                        evidence_ids=tuple(event.evidence_id for event in trade_events[-8:]),
                    )
                )
        return alerts
