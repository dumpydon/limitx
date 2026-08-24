from __future__ import annotations

import argparse
import cProfile
import io
import json
import pstats
from collections.abc import Sequence
from pathlib import Path

from limitx.benchmarks.runner import run_benchmark


def profile_workload(
    *,
    scenario: str,
    operations: int,
    seed: int,
    limit: int,
    output: Path | None = None,
) -> dict[str, object]:
    profiler = cProfile.Profile()
    result = profiler.runcall(
        run_benchmark,
        scenario=scenario,
        operations=operations,
        seed=seed,
        runs=1,
        warmup_operations=min(1_000, operations),
    )
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        profiler.dump_stats(output)

    cumulative_stream = io.StringIO()
    pstats.Stats(profiler, stream=cumulative_stream).strip_dirs().sort_stats(
        pstats.SortKey.CUMULATIVE
    ).print_stats(limit)
    self_stream = io.StringIO()
    pstats.Stats(profiler, stream=self_stream).strip_dirs().sort_stats(
        pstats.SortKey.TIME
    ).print_stats(limit)
    return {
        "workload": result.as_dict(),
        "top_by_cumulative_time": cumulative_stream.getvalue(),
        "top_by_self_time": self_stream.getvalue(),
        "profile_artifact": str(output) if output else None,
        "note": "Profiler overhead invalidates latency values for performance claims.",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Profile a realistic Limit X core workload")
    parser.add_argument("--scenario", choices=["mixed", "cancel_storm", "sweep"], default="mixed")
    parser.add_argument("--operations", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = profile_workload(
        scenario=args.scenario,
        operations=args.operations,
        seed=args.seed,
        limit=args.limit,
        output=args.output,
    )
    print(json.dumps(report["workload"], indent=2, sort_keys=True))
    print("\nTOP BY CUMULATIVE TIME")
    print(report["top_by_cumulative_time"])
    print("TOP BY SELF TIME")
    print(report["top_by_self_time"])
    if report["profile_artifact"]:
        print(f"Profile artifact: {report['profile_artifact']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
