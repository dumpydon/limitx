# Limit X — Interview and Architecture Guide

## What problem does it solve?

An exchange receives requests from buyers and sellers and decides which can trade. A **bid** is a
buy request; an **ask** is a sell request. The best bid is the highest buy price, and the best ask
is the lowest sell price. Their difference is the spread. When compatible requests meet, the
engine creates a trade. Limit X simulates this process for BTC-USD, ETH-USD, AAPL, and MSFT
fixtures. It is offline: it does not connect to a broker, route orders, or represent real money.

## The core flow

`order → validation → risk → symbol queue → matcher → book/events → market-data projection → WebSocket → browser`

FastAPI/Pydantic create commands; the risk gateway checks symbol, quantity, notional, live orders,
position, exposure, and a price collar. A bounded queue sends commands to its symbol worker,
the only task allowed to mutate that book. Matcher emits events and trades. A projection turns
private state into L1/L2 data, and a broker sends snapshots, deltas, and trades to WebSockets.

## Data structures and priority

`PriceIndex` uses `SortedDict` for ordered price levels. A buy index chooses highest; an ask index
chooses lowest. Each `PriceLevel` stores totals and an intrusive doubly linked FIFO queue.
`live_orders` maps an ID directly to its `OrderNode`, so cancelling `LX-123` unlinks it and updates
totals without scanning every order. Expected lookup/unlink is O(1); ordered-level work is around
O(log P), where P is active price levels.

Price-time priority is simple: Alice bids for 5 at 100, then Bob bids for 5 at 100. A seller at 100
reaches Alice first because her accepted sequence is earlier. Better price wins; arrival breaks ties.

## Orders and numeric choices

The implemented order type is limit or market, combined with GTC, IOC, FOK, or post-only
time-in-force. A limit order may rest. A market order has no price and is restricted to IOC or FOK.
IOC trades eligible quantity and cancels its remainder. FOK means “fill the complete quantity now
or do nothing”: the engine preflights eligible FIFO liquidity, so an unfillable FOK does not mutate
the book. Post-only rejects if it would take resting liquidity. Self-trade prevention defaults to
cancelling the incoming taker at the same-account queue head.

Prices and quantities are integers. With a 0.01 tick size, 100.25 is 10025, avoiding binary-float
equality problems. Trades use the resting maker price. A same-price quantity decrease retains
priority; a price change or quantity increase re-inserts the order with new priority.

## Determinism, journal, and recovery

The matcher has no HTTP, WebSocket, or wall-clock dependency. Each mutation advances a logical
sequence and emits an `EngineEvent`. The JSONL journal stores commands, events, and per-symbol
checksums. Replay applies commands to fresh books, compares events, checks invariants, and compares
the canonical hash. Snapshots include live L3 orders, depth, sequence, checksum, and seen IDs;
recovery also stores journal position and risk positions before comparing the rebuilt result.

## Concurrency and market data

Many callers may submit concurrently, but one `SymbolWorker` serializes each symbol. Independent
symbols can use independent queues, while each book keeps one writer and the same ordering model as
replay.

The browser receives a snapshot first. A delta includes its sequence and previous sequence. After
101 and 102, receiving 104 means 103 is missing; the client stops and asks for a fresh snapshot.
Bounded subscriber queues prevent a lagging client from making the matcher wait.

## Simulation, analytics, and UI

`MarketSimulation` uses seeded randomness, seeded liquidity, and maker, noise, momentum, taker, and
whale agents. Scenario weights create normal, thin, cancel-storm, volatility, one-sided, and sweep
regimes. Reusing a seed and scenario reproduces the command stream.

Analytics calculate spread, midpoint, microprice, VWAP, volume, imbalance, lifetime, and slippage.
The ledger tracks integer-tick positions, cash, entry, and P&L. Surveillance flags high cancels,
rapid replacement, layering-like bursts, and large sweeps; an alert is not proof.

The Next.js UI exposes Market Lab, order entry, lifecycle evidence, Replay, Engine X-Ray, Recovery,
Failure Lab, Risk & Surveillance, scenario comparison, and Performance Lab. It can inject transport
faults without changing matcher state.

## Correctness, performance, and Python

Unit tests cover matching edges, FIFO, time-in-force, cancellation, modification, risk, snapshots,
projection, simulation, ledger, and analyst grounding. Hypothesis checks invariants over generated
commands. Differential tests compare production with a separate list-based matcher; integration
tests cover API, replay, recovery, and symbols.

Performance tests time direct `OrderBook.process`, excluding HTTP and browser rendering. **p50** is
the median; **p95** and **p99** mean 95% and 99% of samples are at or below the value. These are
local CPython observations, not HFT guarantees. Python keeps rules and testing clear; a latency-
critical venue would likely move the hot path to Rust or C++.

## Replay Analyst

The Replay Analyst is rule-based, read-only, and outside matching. It summarizes supplied evidence,
retaining only claims whose `event:N` IDs exist. It cannot submit orders or mutate state.

## The explanation I should remember

1. Limit X is a deterministic exchange matching simulator, not a trading venue.
2. The core rule is price-time priority over ordered levels and FIFO queues.
3. Direct node lookup makes cancellation efficient and visible.
4. Integer ticks make comparison, replay, and checksums exact.
5. Mutations create sequenced evidence that can be replayed and verified.
6. One writer owns each symbol book; WebSockets expose its projection.
7. Tests compare invariants, generated workloads, and a reference matcher.
8. Python serves clarity, not production HFT latency.
