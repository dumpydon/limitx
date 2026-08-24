# Invariants

`OrderBook.assert_invariants()` is deliberately callable rather than forced into every benchmark
operation. Tests and audit mode invoke it after mutation.

It verifies:

1. The resting book is not crossed.
2. FIFO priorities are nondecreasing within every price level.
3. Every live remaining quantity is positive and no greater than original quantity.
4. Filled plus remaining quantity equals original quantity.
5. Terminal orders are absent from the live index.
6. Every live order appears exactly once.
7. Every hash-index entry points to the node found in its linked level.
8. Every node's price equals its owning level's price.
9. Aggregate level quantity/count equal the linked orders.
10. Head/tail and previous/next links are reciprocal.
11. Empty price levels are removed.
12. Trade quantities are positive.
13. Event sequence numbers strictly increase.

Buyer/seller conservation is structural: each `TRADE_EXECUTED` carries one quantity used to
decrement both maker and taker. Replay adds the stronger invariant that identical canonical
commands reproduce identical events and a final checksum.

