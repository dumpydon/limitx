# Market data

The matching book is private L3 state. `MarketDataProjector` publishes:

- L1: best bid/ask, spread, doubled midpoint (exact half-tick representation).
- L2: price, aggregate quantity, and order count.
- Recent trades, volume, and VWAP outside the hot path.

Each client first receives `book_snapshot`. A `book_delta` carries its engine sequence and
`previous_sequence`. The browser applies it only if `previous_sequence` equals the last applied
depth sequence. Duplicate, old, or gapped delivery enters `RESYNCING` and fetches a new snapshot.
The UI includes drop/delay/duplicate injection for this transport path; it never alters matcher
state.

The L2 checksum is BLAKE2s over canonical symbol plus aggregate bid/ask depth. It intentionally
excludes account IDs and private L3 priority fields.

WebSocket subscribers use bounded queues. If a browser falls behind, publication clears its stale
queue and inserts a current snapshot. Matching never awaits a slow socket. This sacrifices every
intermediate visual delta while preserving current state and sequence safety.

