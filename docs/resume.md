# Resume material

## One-line description

Built Limit X, a deterministic Python exchange matching-engine and browser-based
market-microstructure laboratory with price-time priority, replay, risk controls, and correctness
verification.

## Resume bullets

- Engineered a fixed-point price-time matcher with linked FIFO price levels, direct O(1) expected
  order lookup/O(1) unlink, atomic FOK, IOC/post-only, priority-aware modification, self-trade
  prevention, and single-writer multi-symbol execution.
- Established correctness through explicit invariants, Hypothesis sequences, 2,640 randomized
  differential commands against an independent oracle, and checksum-verified replay; measured
  170,873 ops/s with 23.625 μs p99 on a 100K mixed laptop workload (3 runs, Apple M2, CPython
  3.14.3).

## 30-second pitch

Limit X is a simulated exchange where the engine—not the dashboard—is the project. Integer ticks,
sorted price levels, linked FIFO queues, and direct node lookup implement deterministic matching
and cancellation. Every command produces sequenced events that drive replay, market data,
analytics, and a live Next.js lab. I verify it with invariants, property tests, and differential
comparison rather than relying only on examples.

## 90-second pitch

I wanted a matching-engine project that survives systems questions. Each symbol has one writer,
so concurrent clients enqueue work but cannot race the book. The book separates sorted price
selection from FIFO orders at each level, and a hash index makes arbitrary cancellation direct.
Prices are integer ticks; FOK preflights liquidity before any mutation; replace rules explicitly
define when priority is lost.

The same sequenced events feed an append-only journal, a checksum-verified replay path, a bounded
WebSocket projection, a deterministic account ledger, and explainable surveillance. A dropped
delta triggers snapshot recovery rather than silent corruption. Seeded agents create normal,
thin, volatile, sweep, selloff, and cancel-storm regimes. Correctness comes from unit edge cases,
full-book invariants, Hypothesis, and a slower list-based oracle. The measured Python numbers are
useful for comparison, but the docs explain honestly why a production hot path would move to
Rust/C++.

## Five talking points

1. Data-structure separation: sorted prices, linked FIFO levels, and direct ID lookup.
2. Atomic exchange semantics: resting price, FOK preflight, STP, and replace priority.
3. Determinism: single writer, logical sequences, stable serialization, snapshots, checksum.
4. Correctness evidence: invariants, properties, differential oracle, replay audit.
5. Honest performance: direct core distributions, real machine metadata, and visible tail noise.

