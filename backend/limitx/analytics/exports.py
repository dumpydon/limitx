from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from limitx.analytics.microstructure import calculate_metrics
from limitx.engine.order_book import OrderBook
from limitx.replay.journal import EventJournal


def export_artifacts(
    root: Path,
    book: OrderBook,
    journal: EventJournal,
    benchmark: dict[str, Any] | None = None,
) -> list[Path]:
    """Export stable, non-pickle schemas into a caller-selected safe directory."""
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    trades_path = root / "trades.csv"
    trade_fields = [
        "sequence",
        "logical_time_ns",
        "trade_id",
        "maker_order_id",
        "taker_order_id",
        "price_ticks",
        "quantity",
        "aggressor_side",
    ]
    with trades_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=trade_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(book.trades)
    written.append(trades_path)

    events_path = root / "events.jsonl"
    with events_path.open("w", encoding="utf-8") as handle:
        for event in book.events:
            handle.write(json.dumps(event.as_dict(), sort_keys=True, separators=(",", ":")) + "\n")
    written.append(events_path)

    depth_path = root / "depth.csv"
    with depth_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["side", "rank", "price_ticks", "quantity", "order_count"],
        )
        writer.writeheader()
        for side in ("bids", "asks"):
            for rank, level in enumerate(book.depth()[side], 1):
                writer.writerow({"side": side.upper(), "rank": rank, **level})
    written.append(depth_path)

    metrics_path = root / "metrics.csv"
    with metrics_path.open("w", newline="", encoding="utf-8") as handle:
        metrics_writer = csv.writer(handle)
        metrics_writer.writerow(["metric", "value"])
        metrics_writer.writerows(sorted(calculate_metrics(book).items()))
    written.append(metrics_path)

    journal.set_checksum(book.symbol, book.checksum())
    session_path = root / "session.jsonl"
    journal.export(session_path)
    written.append(session_path)
    if benchmark is not None:
        benchmark_path = root / "benchmark.json"
        benchmark_path.write_text(json.dumps(benchmark, indent=2, sort_keys=True) + "\n")
        written.append(benchmark_path)
    return written
