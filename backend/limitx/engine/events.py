from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from limitx.domain.enums import EventType


@dataclass(frozen=True, slots=True)
class EngineEvent:
    sequence: int
    event_type: EventType
    symbol: str
    order_id: str | None = None
    logical_time_ns: int = 0
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def evidence_id(self) -> str:
        return f"event:{self.sequence}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "type": self.event_type.value,
            "symbol": self.symbol,
            "order_id": self.order_id,
            "logical_time_ns": self.logical_time_ns,
            **self.data,
        }


def canonical_event(event: EngineEvent) -> tuple[object, ...]:
    """Stable event representation used by differential tests."""
    ignored = {"checksum"}
    data = tuple(sorted((k, str(v)) for k, v in event.data.items() if k not in ignored))
    return (event.event_type.value, event.symbol, event.order_id, data)
