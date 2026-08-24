from __future__ import annotations

import argparse
import json
import platform
import random
import resource
import statistics
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from limitx.domain.commands import CancelOrder, Command, ModifyOrder, NewOrder
from limitx.domain.enums import EventType, OrderType, Side, TimeInForce
from limitx.domain.order import Order
from limitx.engine.order_book import OrderBook


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    scenario: str
    operations: int
    seed: int
    runs: int
    warmup_operations: int
    elapsed_seconds: float
    throughput_ops_per_second: float
    p50_ns: int
    p95_ns: int
    p99_ns: int
    max_ns: int
    trades: int
    cancels: int
    modifies: int
    adds: int
    symbol_count: int
    active_orders: int
    price_levels: int
    max_rss_platform_units: int
    latency_histogram: tuple[dict[str, int | str], ...]
    python_version: str
    platform: str
    processor: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percentile)))
    return ordered[index]


def _workload(
    scenario: str,
    operations: int,
    seed: int,
    symbols: tuple[str, ...],
    add_percent: int | None = None,
    cancel_percent: int | None = None,
) -> list[Command]:
    if scenario not in {"mixed", "cancel_storm", "sweep"}:
        raise ValueError("scenario must be mixed, cancel_storm, or sweep")
    rng = random.Random(seed)
    known: list[tuple[str, str]] = []
    commands: list[Command] = []
    for index in range(operations):
        draw = rng.random()
        if add_percent is None or cancel_percent is None:
            new_cutoff, cancel_cutoff = {
                "mixed": (0.66, 0.88),
                "cancel_storm": (0.18, 0.93),
                "sweep": (0.60, 0.73),
            }[scenario]
        else:
            new_cutoff = add_percent / 100
            cancel_cutoff = (add_percent + cancel_percent) / 100
        if draw < new_cutoff or not known:
            order_id = f"B-{index:09d}"
            symbol = symbols[0] if len(symbols) == 1 else rng.choice(symbols)
            known.append((order_id, symbol))
            side = Side.BUY if rng.getrandbits(1) else Side.SELL
            is_sweep = scenario == "sweep" and rng.random() < 0.35
            commands.append(
                NewOrder(
                    Order(
                        order_id=order_id,
                        symbol=symbol,
                        account_id=f"bench-{rng.randrange(100)}",
                        side=side,
                        order_type=OrderType.MARKET if is_sweep else OrderType.LIMIT,
                        time_in_force=TimeInForce.IOC if is_sweep else TimeInForce.GTC,
                        price_ticks=None if is_sweep else 1_000_000 + rng.randint(-80, 80),
                        quantity=rng.randint(1, 50 if not is_sweep else 250),
                    )
                )
            )
        elif draw < cancel_cutoff:
            order_id, symbol = rng.choice(known)
            commands.append(CancelOrder(symbol, order_id))
        else:
            order_id, symbol = rng.choice(known)
            commands.append(
                ModifyOrder(
                    symbol,
                    order_id,
                    rng.randint(1, 60),
                    1_000_000 + rng.randint(-80, 80),
                )
            )
    return commands


def run_benchmark(
    *,
    scenario: str = "mixed",
    operations: int = 10_000,
    seed: int = 42,
    runs: int = 1,
    warmup_operations: int = 1_000,
    symbol_count: int = 1,
    add_percent: int | None = None,
    cancel_percent: int | None = None,
) -> BenchmarkResult:
    if operations <= 0 or operations > 2_000_000:
        raise ValueError("operations must be between 1 and 2,000,000")
    if runs <= 0 or runs > 20:
        raise ValueError("runs must be between 1 and 20")
    if symbol_count <= 0 or symbol_count > 4:
        raise ValueError("symbol_count must be between 1 and 4")
    if add_percent is not None or cancel_percent is not None:
        if add_percent is None or cancel_percent is None:
            raise ValueError("add_percent and cancel_percent must be provided together")
        if add_percent < 1 or cancel_percent < 0 or add_percent + cancel_percent > 100:
            raise ValueError("invalid operation mix")
    symbols = ("BTC-USD", "ETH-USD", "AAPL", "MSFT")[:symbol_count]
    warmup = _workload(
        scenario,
        min(warmup_operations, operations),
        seed ^ 0xA5A5,
        symbols,
        add_percent,
        cancel_percent,
    )
    warmup_books = {symbol: OrderBook(symbol) for symbol in symbols}
    for command in warmup:
        symbol = command.order.symbol if isinstance(command, NewOrder) else command.symbol
        warmup_books[symbol].process(command)

    all_latencies: list[int] = []
    elapsed_runs: list[float] = []
    total_trades = total_cancels = total_modifies = total_adds = 0
    commands = _workload(
        scenario,
        operations,
        seed,
        symbols,
        add_percent,
        cancel_percent,
    )
    last_books: dict[str, OrderBook] = {}
    for _ in range(runs):
        books = {symbol: OrderBook(symbol) for symbol in symbols}
        latencies: list[int] = []
        started = time.perf_counter_ns()
        for command in commands:
            symbol = command.order.symbol if isinstance(command, NewOrder) else command.symbol
            operation_started = time.perf_counter_ns()
            events = books[symbol].process(command)
            latencies.append(time.perf_counter_ns() - operation_started)
            total_trades += sum(event.event_type is EventType.TRADE_EXECUTED for event in events)
            total_cancels += isinstance(command, CancelOrder)
            total_modifies += isinstance(command, ModifyOrder)
            total_adds += isinstance(command, NewOrder)
        elapsed_runs.append((time.perf_counter_ns() - started) / 1_000_000_000)
        all_latencies.extend(latencies)
        for book in books.values():
            book.assert_invariants()
        last_books = books
    elapsed = statistics.mean(elapsed_runs)
    histogram_bounds = (1_000, 2_500, 5_000, 10_000, 25_000, 50_000, 100_000, 250_000, 1_000_000)
    previous = 0
    histogram: list[dict[str, int | str]] = []
    for bound in histogram_bounds:
        histogram.append(
            {
                "range": f"{previous}-{bound}",
                "upper_ns": bound,
                "count": sum(previous <= value < bound for value in all_latencies),
            }
        )
        previous = bound
    histogram.append(
        {
            "range": f">={previous}",
            "upper_ns": "max",
            "count": sum(value >= previous for value in all_latencies),
        }
    )
    return BenchmarkResult(
        scenario=scenario,
        operations=operations,
        seed=seed,
        runs=runs,
        warmup_operations=len(warmup),
        elapsed_seconds=elapsed,
        throughput_ops_per_second=operations / elapsed,
        p50_ns=_percentile(all_latencies, 0.50),
        p95_ns=_percentile(all_latencies, 0.95),
        p99_ns=_percentile(all_latencies, 0.99),
        max_ns=max(all_latencies),
        trades=total_trades // runs,
        cancels=total_cancels // runs,
        modifies=total_modifies // runs,
        adds=total_adds // runs,
        symbol_count=symbol_count,
        active_orders=sum(len(book.live_orders) for book in last_books.values()),
        price_levels=sum(len(book.bids) + len(book.asks) for book in last_books.values()),
        max_rss_platform_units=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        latency_histogram=tuple(histogram),
        python_version=platform.python_version(),
        platform=platform.platform(),
        processor=platform.processor() or platform.machine(),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark the Limit X core matcher directly")
    parser.add_argument("--scenario", choices=["mixed", "cancel_storm", "sweep"], default="mixed")
    parser.add_argument("--orders", "--operations", dest="operations", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--warmup", type=int, default=1_000)
    parser.add_argument("--symbols", type=int, default=1)
    parser.add_argument("--add-percent", type=int)
    parser.add_argument("--cancel-percent", type=int)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    result = run_benchmark(
        scenario=args.scenario,
        operations=args.operations,
        seed=args.seed,
        runs=args.runs,
        warmup_operations=args.warmup,
        symbol_count=args.symbols,
        add_percent=args.add_percent,
        cancel_percent=args.cancel_percent,
    )
    payload = result.as_dict()
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
