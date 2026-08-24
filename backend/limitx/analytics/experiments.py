from __future__ import annotations

import statistics
import time
from typing import Any

from limitx.analytics.microstructure import calculate_metrics
from limitx.domain.instruments import INSTRUMENTS
from limitx.simulation.engine import MarketSimulation


def _percentile(values: list[int], ratio: float) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * ratio))]


def run_scenario_experiment(
    scenario: str,
    *,
    symbol: str,
    seed: int,
    operations: int,
) -> dict[str, Any]:
    simulation = MarketSimulation(
        symbol=symbol,
        seed=seed,
        scenario=scenario,
        center_ticks=INSTRUMENTS[symbol].reference_price_ticks,
    )
    simulation.seed_book()
    spreads: list[int] = []
    latencies: list[int] = []
    for _ in range(operations):
        started = time.perf_counter_ns()
        simulation.step()
        latencies.append(time.perf_counter_ns() - started)
        if simulation.book.best_bid is not None and simulation.book.best_ask is not None:
            spreads.append(simulation.book.best_ask - simulation.book.best_bid)
    simulation.book.assert_invariants()
    metrics = calculate_metrics(simulation.book)
    return {
        "scenario": scenario,
        "seed": seed,
        "operations": operations,
        "average_spread_ticks": statistics.mean(spreads) if spreads else None,
        "median_spread_ticks": statistics.median(spreads) if spreads else None,
        "trade_count": len(simulation.book.trades),
        "volume": metrics["trade_volume"],
        "vwap_ticks": metrics["vwap_ticks"],
        "price_impact_ticks": metrics["last_price_impact_ticks"],
        "cancel_add_ratio": metrics["cancel_to_add_ratio"],
        "fill_ratio": metrics["fill_ratio"],
        "p99_operation_ns": _percentile(latencies, 0.99),
        "checksum": simulation.book.checksum(),
    }


def compare_scenarios(
    left: str,
    right: str,
    *,
    symbol: str,
    seed: int,
    operations: int,
) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "seed": seed,
        "operations": operations,
        "left": run_scenario_experiment(left, symbol=symbol, seed=seed, operations=operations),
        "right": run_scenario_experiment(right, symbol=symbol, seed=seed, operations=operations),
        "caution": "Single deterministic runs are descriptive, not statistical significance.",
    }
