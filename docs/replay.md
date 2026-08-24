# Journal, snapshots, and replay

The journal is append-only canonical JSONL:

1. Header with schema version and session ID.
2. Monotonic command entries containing the normalized command and emitted events.
3. Footer with per-symbol final checksums.

Commands—not wall-clock timestamps—are the recovery source of truth. Replay creates fresh books,
applies commands in journal order, compares the exact serialized event output, runs invariants,
and checks the final state hash.

Snapshots capture symbol, engine sequence, tick size, live L3 orders, aggregate L2 depth, count,
checksum, and the previously seen order-ID set required to preserve duplicate-ID rejection after
recovery. `OrderBook.from_snapshot` rebuilds every level/node/index entry and rejects a tampered
checksum. The Recovery Demonstration captures the journal position and symbol risk positions,
allows continued mutation, then loads the snapshot, replays only later commands, compares every
emitted event, runs invariants, and compares expected versus recovered final checksums.

Interactive replay intentionally reconstructs from command zero for arbitrary timeline jumps.
The CPU-heavy jump runs away from the API event loop, while invariants are checked at the selected
reconstruction boundary. `step()` can still return a snapshot for a true single-step action, while
bulk `jump()` suppresses intermediate L3 serialization and emits only the requested final state.
Snapshot recovery demonstrates the faster warm-start path separately.

The state checksum is the first 16 hexadecimal characters of SHA-256 over canonical JSON
containing symbol, sequence, and all live bid/ask orders in priority order. It is distinct from
the lightweight L2 projection checksum used for WebSocket resynchronization.

```bash
python -m limitx.audit data/session.jsonl
```

The auditor fails on malformed JSON, a non-monotonic command sequence, event divergence,
invariant failure, or final checksum mismatch.
