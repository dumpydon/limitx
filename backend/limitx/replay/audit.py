from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from limitx.replay.journal import EventJournal
from limitx.replay.replay import ReplaySession


def audit(path: Path) -> dict[str, object]:
    journal = EventJournal.load(path)
    result = ReplaySession(journal).run(compare_events=True)
    for book in result.books.values():
        book.assert_invariants()
    return {
        "session_id": journal.session_id,
        "commands_replayed": result.commands_replayed,
        "checksums": result.checksums,
        "expected_checksums": journal.final_checksums,
        "divergences": list(result.divergences),
        "valid": not result.divergences,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a Limit X JSONL session")
    parser.add_argument("session", type=Path)
    args = parser.parse_args(argv)
    report = audit(args.session)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
