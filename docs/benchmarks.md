# Benchmark methodology and results

## Environment

- Apple M2 MacBook Air, 8 GB RAM
- arm64, macOS 15.7.8 (Darwin 24.6.0)
- CPython 3.14.3
- Seed 42
- `time.perf_counter_ns()` around each direct `OrderBook.process` call
- One pre-run warm-up; 3 measured runs except the one-million operation observation

The workload is generated before timing. HTTP, Pydantic, JSON serialization, WebSockets, React,
and UI rendering are excluded. Matcher event object creation and in-memory event/trade retention
are included. Percentiles pool operation samples across runs; throughput uses operations divided
by mean run elapsed time.

## Second-pass results measured on this machine

| Scenario | Ops | Symbols | Runs | Warm-up | Throughput | p50 | p95 | p99 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Mixed | 10K | 1 | 3 | 1K | 181,623/s | 4.167 μs | 14.333 μs | 23.292 μs | 4.745 ms |
| Mixed | 100K | 1 | 3 | 5K | 173,825/s | 4.209 μs | 14.291 μs | 22.959 μs | 56.103 ms |
| Cancel storm | 100K | 1 | 3 | 5K | 346,027/s | 1.125 μs | 5.708 μs | 14.875 μs | 22.299 ms |
| Mixed | 100K | 4 | 3 | 5K | 168,825/s | 4.292 μs | 14.375 μs | 21.584 μs | 88.632 ms |
| Mixed memory stress | 1M | 1 | 1 | 10K | 96,950/s | 5.709 μs | 20.042 μs | 28.250 μs | 1.110 s |

The 100K one-symbol mixed run averaged 17,327 trades, 22,188 cancel commands, 12,022
modifications, and 65,790 adds. It finished with 9,400 active orders across 79 price levels.
The cancel-storm is a synthetic 75%-cancel workload; it is not an industry traffic claim.

The 1M run's throughput decline, roughly 1.28 GB maximum RSS, and 1.110 s maximum outlier are
reported rather than hidden. The complete event/trade history grows through the run, and CPython
allocation, GC, OS scheduling, CPU power state, and timer overhead affect the distribution. These
results cannot be described as HFT latency or production capacity.

## Profile-guided FOK guard

The second-pass evidence payload initially computed `_available_liquidity()` for every submitted
order, even though only FOK semantics require the atomic preflight. cProfile made that unnecessary
walk visible in the `submit` cumulative path. The safe change moved the walk under the existing
`TimeInForce.FOK` branch; semantics and tests remained unchanged.

Identical workload comparison: mixed, 100K operations, seed 42, 5K warm-up, three runs.

| Build | Throughput | p50 | p95 | p99 |
|---|---:|---:|---:|---:|
| Evidence pass before guard | 141,824/s | 5.292 μs | 15.667 μs | 26.375 μs |
| After FOK-only guard | 180,506/s | 4.209 μs | 14.042 μs | 20.916 μs |

Observed on this machine: +27.3% throughput and -20.7% p99. This is a paired local observation,
not a statistical or cross-machine guarantee. Raw JSON results are stored under
`data/benchmarks/second-pass-{before,after}-fok-guard.json`.

## Profiling

A 20K mixed cProfile run showed cumulative time concentrated in `OrderBook.process`, `submit`,
`_execute_accepted`, event construction, and repeated best-price access through
`SortedDict.peekitem`. Profiling output is intentionally not used for latency claims. Use:

```bash
scripts/profile.sh 20000
python -m limitx.profile --scenario mixed --operations 20000 --output /tmp/limitx.prof
python -X tracemalloc -m limitx.bench --orders 100000 --seed 42
```

Core optimization removed a full L3 state checksum from every `BOOK_UPDATED` event; lightweight
L2 transport checksums remain in the projection layer, while full checksums are computed for
snapshots, replay, audit, system inspection, and export.
