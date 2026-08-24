from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from limitx.domain.commands import Command, command_from_dict, command_to_dict
from limitx.engine.events import EngineEvent


@dataclass(frozen=True, slots=True)
class JournalEntry:
    command_sequence: int
    command: dict[str, object]
    events: tuple[dict[str, Any], ...]


class EventJournal:
    """In-memory append log with stable JSONL import/export.

    Commands are the replay source of truth; recorded events are retained for audit comparison.
    """

    def __init__(self, session_id: str = "default", *, risk_enabled: bool = False) -> None:
        self.session_id = session_id
        self.risk_enabled = risk_enabled
        self.entries: list[JournalEntry] = []
        self.final_checksums: dict[str, str] = {}

    def record(self, command: Command, events: list[EngineEvent]) -> None:
        self.entries.append(
            JournalEntry(
                command_sequence=len(self.entries) + 1,
                command=command_to_dict(command),
                events=tuple(event.as_dict() for event in events),
            )
        )

    def set_checksum(self, symbol: str, checksum: str) -> None:
        self.final_checksums[symbol] = checksum

    def commands(self) -> list[Command]:
        return [command_from_dict(entry.command) for entry in self.entries]

    def export(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            header = {
                "record": "header",
                "version": 1,
                "session_id": self.session_id,
                "risk_enabled": self.risk_enabled,
            }
            handle.write(json.dumps(header, sort_keys=True, separators=(",", ":")) + "\n")
            for entry in self.entries:
                payload = {
                    "record": "entry",
                    "command_sequence": entry.command_sequence,
                    "command": entry.command,
                    "events": entry.events,
                }
                handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
            footer = {"record": "footer", "checksums": self.final_checksums}
            handle.write(json.dumps(footer, sort_keys=True, separators=(",", ":")) + "\n")

    @classmethod
    def load(cls, path: Path) -> EventJournal:
        journal: EventJournal | None = None
        expected_command_sequence = 1
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(f"invalid JSON on line {line_number}") from error
                record = payload.get("record")
                if record == "header":
                    if journal is not None:
                        raise ValueError("duplicate journal header")
                    journal = cls(
                        str(payload["session_id"]),
                        risk_enabled=bool(payload.get("risk_enabled", False)),
                    )
                elif record == "entry":
                    if journal is None:
                        raise ValueError("entry before header")
                    if int(payload["command_sequence"]) != expected_command_sequence:
                        raise ValueError("non-monotonic command sequence")
                    journal.entries.append(
                        JournalEntry(
                            command_sequence=expected_command_sequence,
                            command=dict(payload["command"]),
                            events=tuple(dict(event) for event in payload["events"]),
                        )
                    )
                    expected_command_sequence += 1
                elif record == "footer":
                    if journal is None:
                        raise ValueError("footer before header")
                    journal.final_checksums = dict(payload.get("checksums", {}))
                else:
                    raise ValueError(f"unknown journal record on line {line_number}")
        if journal is None:
            raise ValueError("missing journal header")
        return journal
