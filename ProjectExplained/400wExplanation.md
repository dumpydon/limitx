# Limit X in 400 Words

Limit X is a simulated exchange and matching-engine laboratory built mainly in Python. It does
not connect to a broker, place real trades, or handle real money. Its purpose is to make the rules
and engineering of an exchange visible, repeatable, and testable.

An order book is simply a list of waiting buy and sell requests. A buy request is a **bid**; a sell
request is an **ask**. Each request has a price and quantity. For example, a bid for 10 units at
100 waits until someone is willing to sell at 100 or less. The gap between the best bid and best
ask is the spread.

The matching engine owns one book per symbol. When a new order arrives, it validates the request,
then checks the risk gateway, and finally tries to match it against the opposite side. The best
price wins: the highest bid and lowest ask are considered first. If several orders have the same
price, the earlier accepted order wins. This is price-time priority. Trades execute at the resting
order's price. Unfilled limit orders can remain in the book; market and IOC remainders are
cancelled, while FOK first checks that its complete quantity is available.

The book uses integer price ticks instead of binary floating-point prices. With a 0.01 tick size,
100.25 is stored as 10025. Price levels are kept in an ordered `SortedDict`. Each level contains
an intrusive doubly linked FIFO queue, and a dictionary maps an order ID directly to its live node.
That separation makes best-price selection, FIFO matching, and arbitrary cancellation explicit.
Modification also has a deliberate rule: a same-price quantity decrease keeps priority, while a
price change or quantity increase loses it.

Every state-changing command creates sequenced events. An append-only JSONL journal stores the
commands and resulting events. Snapshots, canonical state checksums, replay, and recovery verify
that the same inputs rebuild the same book. A separate risk gateway enforces quantity, notional,
live-order, position, exposure, price-collar, and symbol limits.

The browser is a Next.js laboratory, not the source of truth. It receives L1/L2 market-data
projections and trades over WebSockets, detects sequence gaps, and requests a fresh snapshot when
needed. It exposes the book, order ticket, lifecycle evidence, replay, Engine X-Ray, failure
injection, risk/surveillance tools, scenario simulation, and measured benchmarks.

Limit X is useful because it joins data structures, event-driven design, correctness testing,
recovery, observability, and performance measurement in one inspectable system. It demonstrates
how a small exchange core can be explained and challenged without pretending to be production HFT.
