# Interview guide

## Thirty-second architecture answer

Each symbol has one writer consuming a bounded queue. The writer owns a sorted price index,
linked FIFO levels, and a hash map from order ID to node. Integer ticks make crossing exact.
Commands emit stable sequenced events into a journal and a separate L1/L2 projection. Replay
rebuilds state and verifies a checksum; unit, property, and differential tests verify semantics.

## Likely questions

**Why Python?** Clarity, property testing, simulation tooling, and a readable reference behavior
were the priorities. The measured tails also demonstrate why I would move a production hot path
to Rust/C++.

**Why price-time priority?** It is a deterministic, widely understood central-limit-book rule:
better prices win, then earlier accepted sequence at a price.

**Why fixed-point integers?** A cross must not depend on binary floating equality. `$100.25` is
`10025` ticks; formatting is an adapter concern.

**Why not a heap?** A heap finds a best item but arbitrary cancellation needs index maintenance or
tombstones. Ordered levels plus direct linked-node removal make ownership and cleanup explicit.

**How is cancellation efficient?** `live_orders[id]` finds the intrusive node in expected O(1),
then previous/next pointers unlink it in O(1). Removing the now-empty price level is O(log P).

**Why a linked list?** FIFO append, head consumption, and arbitrary unlink are all O(1) once the
node is known. A deque does not offer O(1) middle removal.

**Why single writer?** It prevents concurrent pointer mutation, eliminates book-level lock races,
stabilizes sequence order, and makes live/replay behavior easy to compare. Symbols remain
independent.

**Is FOK atomic?** Yes. `_available_liquidity` walks only price-eligible FIFO liquidity and stops
at cancel-taker STP. Rejection occurs before acceptance or mutation. Unit and differential tests
cover insufficient and complete cases.

**What does replay buy?** Reproducible incidents, deterministic debugging, recovery validation,
offline analytics, and evidence IDs for explanations.

**What if a WebSocket client falls behind?** Its bounded queue is cleared and replaced by a
snapshot. The client also compares `previous_sequence`; a gap triggers resync instead of blind
application.

**How do you prove recovery from a mid-session snapshot?** The recovery point stores L3 live
orders, seen IDs, engine sequence, checksum, journal position, and symbol risk positions. The lab
continues trading, reconstructs from that point, replays only subsequent commands, compares event
output, runs invariants, and requires the final checksum to match.

**Is Engine X-Ray a mock diagram?** No. The endpoint reads the current `PriceIndex`, selected
`PriceLevel`, head/tail, every displayed node's real previous/next pointers, and the live order
index. It has no second copy of book state.

**How do you guarantee correctness?** Explicit invariants plus an edge-case matrix, Hypothesis
sequences, a structurally separate reference matcher, event-equivalent replay, and checksum audit.

**What does property testing catch?** Interactions humans do not enumerate well—such as invalid
modifies after partial fills, deleting and recreating levels, repeated cancels, and TIF mixes.

**What is p99?** Ninety-nine percent of sampled operations completed at or below that value. It is
not a worst case and is sensitive to workload and environment.

**Why are these not HFT numbers?** They are one CPython process on a laptop, include allocation and
runtime noise, and lack native networking, kernel bypass, CPU pinning, calibrated clocks, and
production durability.

**How would you migrate the hot path?** Freeze the command/event contract, implement a Rust/C++
engine behind it, and require all current unit, replay, property-derived fixtures, and differential
cases to remain equivalent.

**How would you scale to 10,000 symbols?** Partition symbols across a bounded number of worker
processes by stable hash and activity, preserve one writer per symbol, isolate noisy symbols, and
route market-data subscriptions separately. Ten thousand OS processes are unnecessary.

**How does crash recovery work?** Load the latest checksum-verified snapshot, replay later
canonical commands, assert invariants, and compare the expected final checksum before serving.

**What changes in production?** A native matcher, durable replicated write-ahead log, binary
protocols, precise clock discipline, authorization, drop-copy, operational controls, redundancy,
schema evolution, disaster recovery, and independent conformance testing.

**How did profiling change the code?** cProfile showed `_available_liquidity` in every submit after
adding FOK evidence. It should only run for FOK. Guarding it restored the intended semantics and on
the identical local 100K/seed-42/three-run workload changed observed throughput from 141,824 to
180,506 ops/s and p99 from 26.375 to 20.916 μs. Tests passed before either result was accepted.
