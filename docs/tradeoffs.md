# Design trade-offs

## Python deliberately

Python provides concise exchange semantics, rapid invariant instrumentation, excellent property
testing, deterministic simulation libraries, and an implementation that can be explained line by
line. It also has interpreter overhead, the GIL, frequent object allocation, GC/runtime tail
behavior, weaker cache locality, and no credible claim to production ultra-low latency.

The current design therefore targets correctness research, interview inspection, API demos, and
performance-aware experimentation—not live venue infrastructure.

## Plausible production evolution

```text
Python validation / simulation / reference model / analytics
                         │
                         ▼
             Rust or C++ matching core
                         │
                         ▼
               equivalent event schema
```

The reference/differential fixtures would become compatibility tests for the native engine.
Network protocol, durable replicated log, clock discipline, crash-consistent snapshots,
redundancy, operational controls, regulatory audit, authentication, and disaster recovery would
also need production designs. None is implied by this repository.

## Other decisions

- A modular monolith avoids fake distributed complexity.
- Full invariant scans are opt-in for audit/tests rather than charged to each benchmark op.
- Full L3 checksums are recovery artifacts; lightweight L2 checksums protect market-data sync.
- Subscriber overflow drops stale deltas and sends current state instead of blocking matching.
- Surveillance labels patterns as deterministic heuristics, never proof of manipulation.
- The deterministic analyst works without an API key and cannot submit commands.
