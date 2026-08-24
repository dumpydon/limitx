# Resume material

## One-line description

Built Limit X, a deterministic Python exchange matching engine and market-microstructure
observatory with price-time execution, evidence-backed lifecycle inspection, checksum recovery,
sequence-safe market data, and an engineering-focused browser lab.

## Two-bullet version

- Engineered a fixed-point price-time matcher with linked FIFO price levels, direct O(1) expected
  order lookup/O(1) unlink, atomic FOK, IOC/post-only, priority-aware modification, self-trade
  prevention, deterministic risk, and independent single-writer symbol workers.
- Established correctness through 30 tests, explicit invariants, Hypothesis sequences, 2,640
  differential commands against an independent oracle, and snapshot/journal checksum recovery;
  measured 173,825 ops/s with 22.959 μs p99 on a 100K mixed Apple M2/CPython 3.14.3 workload
  (seed 42, three runs).

## Three-bullet version

- Designed a deterministic central-limit-order-book simulator using integer ticks, a sorted price
  index, intrusive doubly linked FIFO queues, direct cancellation, resting-price execution, and
  explicit IOC/FOK/post-only/STP/replace-priority semantics.
- Built an event-sourced observability layer with structured evidence, lifecycle and multi-level
  match visualization, L1/L2 snapshot+delta recovery, Engine X-Ray, risk/surveillance consoles,
  scenario experiments, grounded replay analysis, and checksum-verified crash-recovery patterns.
- Used property/differential testing and cProfile to protect correctness and guide optimization;
  an FOK-only preflight guard improved an identical local 100K workload from 141,824 to 180,506
  ops/s (+27.3%) and reduced p99 from 26.375 to 20.916 μs (-20.7%).

## 30-second pitch

Limit X is a simulated exchange where the engine—not a decorative dashboard—is the project.
Integer ticks, sorted price levels, linked FIFO queues, and direct node lookup implement
deterministic price-time matching. Every command produces sequenced evidence that powers replay,
recovery, market data, lifecycle explanations, and a live engineering terminal. Correctness comes
from invariants, property tests, and differential comparison rather than example tests alone.

## 90-second pitch

Each symbol has one writer, so concurrent clients enqueue commands but cannot race the pointer-rich
book. The book separates sorted price selection from FIFO execution at a level, while a hash index
makes arbitrary cancellation direct. Prices are integer ticks, FOK walks eligible liquidity before
any mutation, trades execute at resting prices, and replace rules explicitly define priority loss.

The same events drive an append-only journal, a bounded sequence-aware WebSocket projection, an
exact account ledger, surveillance rules, and a read-only analyst whose claims must cite stored
evidence. The UI can inspect the actual price level and nodes, drop a market-data delta and recover,
or load a snapshot and replay only subsequent commands to the same checksum. Unit, Hypothesis,
differential, API, audit, and browser tests establish correctness. Local performance is measured as
a distribution and documented with its environment and memory/tail limitations.

## System-design pitch

The command gateway validates and applies deterministic pre-trade risk, then routes to a bounded
per-symbol queue. One task owns each book and its sequencer. Matcher events fan out to the journal,
ledger/analytics/surveillance, and an L1/L2 projector. Slow WebSocket clients cannot block matching:
bounded subscriber overflow replaces stale deltas with a snapshot. Clients also compare
`previous_sequence` and stop on gaps. Recovery loads L3 state, sequence, seen IDs, and risk state,
then replays later journal commands and validates event output, invariants, and checksums.

## Quantitative / low-latency engineering pitch

The project is performance-aware but intentionally honest about Python. Direct cancellation is
expected O(1) lookup plus O(1) unlink; ordered level updates are approximately O(log P), and
matching scales with consumed orders/levels. A final 100K mixed run observed 173,825 ops/s and
22.959 μs p99 locally; a one-million-operation memory stress retained all event/trade history,
reached about 1.28 GB max RSS, and showed a 1.110 s tail outlier. That tail is evidence for moving a live
latency-critical hot path to Rust/C++ while keeping Python as the reference, simulation, and
research surface—not evidence for a speed claim.

## AI engineering pitch

Replay Analyst is downstream and read-only. It receives structured engine facts, emits claims with
`event:N` evidence IDs, and passes through a validator that removes claims with absent evidence.
The deterministic fallback works without an API key and cannot mutate matching state. The UI shows
claims beside their evidence, while lifecycle explanations answer common “why” questions directly
from rules before any model is involved.
