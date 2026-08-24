# Testing strategy

- Unit tests cover empty books, exact/non-crossing orders, resting-price execution, partial and
  multi-level fills, FIFO, market/IOC/FOK/post-only, duplicate/invalid orders, cancellation,
  modify priority, self-trade prevention, snapshots, risk, ledger, projections, AI grounding, and
  seeded simulation.
- Hypothesis generates up to 70 mixed new/cancel/modify operations with invalid quantities,
  randomized prices, both sides, both order types, and all TIF values. Invariants run after every
  operation.
- Differential testing sends 2,640 randomized commands (12 seeds × 220) through both the
  production matcher and a separate O(N log N), list-based reference oracle. It compares every
  trade, live order, and aggregated depth state.
- Replay integration exports JSONL, reloads it, compares emitted events, validates invariants,
  and checks the final checksum.
- API integration verifies application lifespan, seeded snapshots, typed order entry, direct
  cancellation, invalid market semantics, multi-symbol summaries, journal-backed lifecycle,
  real Engine X-Ray data, snapshot-plus-journal recovery, regime comparison, and custom
  multi-symbol benchmark inputs.
- Frontend checks run strict TypeScript, ESLint, a production build, and browser exercises for
  simulation, manual orders, replay, benchmark output, fault recovery, and responsive stacking.

Browser validation has caught and fixed four real defects across the two passes: a replay client
using GET for a POST endpoint; duplicate client resynchronizations racing after one dropped delta;
and long-session replay performing a full invariant scan after every command, producing
quadratic behavior and blocking the API loop; then a second measurement found bulk replay still
serializing a full L3 snapshot after every step. Replay now checks invariants and serializes state
once at the reconstructed boundary, and runs the CPU-heavy jump off the event loop. A measured
5,024-command endpoint call fell from 5.19 seconds to 99 ms on this machine.

The current suite contains 30 tests. The differential test still drives 2,640 randomized commands
through the independent reference matcher, and Hypothesis remains part of the full pytest gate.

Run all required checks with `make lint typecheck test frontend-check`.
