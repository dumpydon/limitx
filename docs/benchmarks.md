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

## Results measured on this machine

| Scenario | Ops | Runs | Warm-up | Throughput | p50 | p95 | p99 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Mixed | 10K | 3 | 1K | 191,789/s | 4.250 μs | 14.375 μs | 21.875 μs | 2.984 ms |
| Mixed | 100K | 3 | 5K | 170,873/s | 4.333 μs | 14.500 μs | 23.625 μs | 41.508 ms |
| Cancel storm | 100K | 3 | 5K | 342,972/s | 1.125 μs | 5.625 μs | 15.291 μs | 35.816 ms |
| Mixed | 1M | 1 | 10K | 91,189/s | 5.834 μs | 20.500 μs | 30.292 μs | 1.256 s |

The 100K mixed run averaged 17,327 trades, 22,188 cancel commands, and 12,022 modifications.
The cancel-storm is a synthetic 75%-cancel workload; it is not an industry traffic claim.

The 1M run's throughput decline and maximum outlier are reported rather than hidden. The complete
event/trade history grows through the run, and CPython allocation, GC, OS scheduling, CPU power
state, and timer overhead affect the distribution. These results cannot be described as HFT
latency or production capacity.

## Profiling

A 20K mixed cProfile run showed cumulative time concentrated in `OrderBook.process`, `submit`,
`_execute_accepted`, event construction, and repeated best-price access through
`SortedDict.peekitem`. Use:

```bash
scripts/profile.sh 20000
python -X tracemalloc -m limitx.bench --orders 100000 --seed 42
```

Core optimization removed a full L3 state checksum from every `BOOK_UPDATED` event; lightweight
L2 transport checksums remain in the projection layer, while full checksums are computed for
snapshots, replay, audit, system inspection, and export.

