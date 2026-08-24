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
  cancellation, and invalid market semantics.
- Frontend checks run strict TypeScript, ESLint, a production build, and browser exercises for
  simulation, manual orders, replay, benchmark output, fault recovery, and responsive stacking.

One real bug caught during browser validation was a replay client using GET for the backend's POST
load endpoint. It was fixed and revalidated against a 2,528-command live journal.

Run all required checks with `make lint typecheck test frontend-check`.

