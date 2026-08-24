from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from limitx.engine.order_book import OrderBook

SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


class SnapshotStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        if not SAFE_NAME.fullmatch(name):
            raise ValueError("invalid snapshot name")
        return self.root / f"{name}.json"

    def save(self, name: str, book: OrderBook) -> Path:
        path = self._path(name)
        path.write_text(
            json.dumps(book.snapshot(), sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        return path

    def load(self, name: str) -> OrderBook:
        payload: dict[str, Any] = json.loads(self._path(name).read_text(encoding="utf-8"))
        return OrderBook.from_snapshot(payload)
