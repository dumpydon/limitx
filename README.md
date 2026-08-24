# Limit X

Deterministic exchange matching-engine and market-microstructure laboratory implemented in
Python. Limit X models price-time-priority execution, advanced time-in-force semantics,
deterministic event replay, risk controls, seeded market regimes, microstructure analytics, and
measured core-engine performance.

The project intentionally prioritizes correctness and inspectability over claims of production
HFT latency. It is a simulated venue: it has no broker integration and never routes real orders.

## Demo

```bash
make install
make run-backend   # terminal 1
make run-frontend  # terminal 2
```

Open `http://localhost:3000`, press **Run market**, and the default seed `42` immediately produces
a live ladder, cumulative depth, execution tape, analytics, and replayable command journal.
`docker compose up --build` provides the same backend/frontend pair.

## Engineering highlights

- Integer-tick matching with resting-price execution and strict price-time priority.
- Explicit price levels containing intrusive doubly linked FIFO queues; a hash map points order
  IDs directly to live nodes for O(1) lookup and O(1) unlink after lookup.
- Limit, market, GTC, IOC, atomic FOK, post-only, partial fill, cancel, priority-aware modify, and
  cancel-taker self-trade prevention semantics.
- A single-writer command task per symbol, append-only command/event journal, state snapshots,
  stable JSON, deterministic replay, and SHA-256 state checksums.
- Separate risk gateway, L1/L2 projection, sequence-linked deltas, bounded WebSocket subscriber
  queues, and snapshot recovery after a delta gap.
- Seeded noise, market-making, momentum, taker, and whale agents across nine market regimes,
  including a synthetic cancel storm.
- Explicit invariant checks, deterministic edge-case tests, Hypothesis property tests, and
  thousands of randomized differential operations against a separate list-based oracle.
- Microstructure analytics, an exact tick-based account ledger, explainable surveillance
  heuristics, exportable artifacts, and a read-only evidence-grounded Replay Analyst.

## Architecture

```mermaid
flowchart LR
    C[Concurrent clients] --> G[Validation + risk gateway]
    G --> Q{Symbol queue}
    Q -->|BTC-USD| B[Single-writer matcher]
    Q -->|ETH-USD| E[Independent matcher]
    B --> J[Append-only journal]
    B --> P[L1/L2 projection]
    B --> A[Ledger + analytics]
    P --> W[Bounded WebSocket queues]
    W --> U[Next.js laboratory]
    J --> R[Replay + audit]
    R --> H[Checksum verification]
```

The pure package under `backend/limitx/engine` imports no FastAPI, browser, or WebSocket code.
See [architecture](docs/architecture.md), [matching semantics](docs/matching-semantics.md), and
[data structures](docs/data-structures.md).

## Matching semantics

Prices are integer ticks (`$100.25 → 10025`) and quantities are integers. Best price wins; an
order's `accepted_sequence` breaks ties at a price. Trades execute at the resting order's price.
FOK walks eligible FIFO liquidity before accepting and therefore never partially mutates the
book. A same-price quantity decrease retains priority; a price change or quantity increase loses
it. Post-only rejects rather than taking. Market and IOC remainders cancel.

## Correctness strategy

`OrderBook.assert_invariants()` checks topology, aggregates, lifecycle conservation, index
identity, FIFO order, uncrossed state, positive trades, and sequence monotonicity. The test suite
adds an independently structured `ReferenceBook`, replay event equivalence, snapshot tamper
detection, API tests, and Hypothesis-generated command sequences.

```bash
make lint
make typecheck
make test
make frontend-check
```

## Measured benchmarks

Core-only measurements taken on this machine (Apple M2, 8 GB RAM, macOS 15.7.8, CPython 3.14.3)
after tests and replay checks passed:

| Workload | Operations | Runs | Throughput | p50 | p95 | p99 |
|---|---:|---:|---:|---:|---:|---:|
| Mixed | 10,000 | 3 | 191,789 ops/s | 4.250 μs | 14.375 μs | 21.875 μs |
| Mixed | 100,000 | 3 | 170,873 ops/s | 4.333 μs | 14.500 μs | 23.625 μs |
| Cancel storm | 100,000 | 3 | 342,972 ops/s | 1.125 μs | 5.625 μs | 15.291 μs |
| Mixed | 1,000,000 | 1 | 91,189 ops/s | 5.834 μs | 20.500 μs | 30.292 μs |

These are local CPython observations, not production guarantees. The one-million-operation run
retained the complete event/trade history and exhibited a 1.256 s maximum outlier, illustrating
runtime, GC, memory-growth, and scheduler noise. See [benchmark methodology](docs/benchmarks.md).

```bash
python -m limitx.bench --scenario mixed --orders 100000 --seed 42 --runs 3
```

## Replay and audit

Commands and their resulting structured events are serialized as canonical JSONL. Replay
re-runs commands through fresh per-symbol books, compares event output, checks invariants, and
compares final checksums.

```bash
python -m limitx.audit data/session.jsonl
python scripts/export_demo.py  # events.jsonl, session.jsonl, trades/depth/metrics CSV
```

## API

FastAPI exposes health, symbols, book/depth, trades, order submit/cancel/modify, live orders,
simulation controls, metrics, system state, replay, benchmarks, exports, analyst, and
`/ws/market/{symbol}`. OpenAPI is available at `http://localhost:8000/docs`.

## Project map

```text
backend/limitx/
  domain/       explicit orders, commands, enums and value types
  engine/       matcher, FIFO levels, sorted index, events, symbol workers
  risk/         deterministic pre-trade limits
  market_data/  L1/L2 snapshot, deltas, checksum, bounded broker
  replay/       JSONL journal, snapshots, replay and audit CLI
  simulation/   seeded agents and market regimes
  analytics/    metrics, ledger, surveillance and exports
  reference/    slower list-based differential oracle
  benchmarks/   direct core-engine workloads and percentile reports
  ai/           read-only rule-based grounded analyst
  api/          FastAPI adapter
frontend/       strict TypeScript Next.js laboratory UI
docs/           decisions, semantics, testing, replay and interview guide
```

## Scope and trade-offs

Python makes the semantics inspectable and the correctness tooling unusually strong. It also
brings interpreter overhead, allocation cost, the GIL, GC pauses, and unsuitable tail behavior
for a latency-critical native matcher. A plausible production evolution keeps Python for
the gateway, simulation, analytics, and reference behavior while moving the equivalent hot path
to Rust or C++. Limit X deliberately does not claim that migration has happened.

Further reading: [trade-offs](docs/tradeoffs.md), [testing](docs/testing.md),
[market data](docs/market-data.md), [AI grounding](docs/ai-grounding.md), and the
[interview guide](docs/interview-guide.md).
