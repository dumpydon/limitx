# Product and interview demo guide

Limit X opens directly into a populated, deterministic BTC-USD simulation. All displayed
movement is produced by backend commands passing through the matcher; the browser never invents
prices or trades.

The X in the custom header mark is the activity anchor. It remains calm at rest, previews the
selected side on BUY/SELL hover, and acknowledges accepted orders, executions, multi-level sweeps,
risk rejections, and client resynchronization from actual event results. Rapid executions are
coalesced; reduced-motion users receive the same semantic color without transforms.

## First five minutes

1. **Market Lab:** observe the realistic synthetic instrument fixtures, independent symbol
   workers, best bid/ask, spread/mid/bps, cumulative totals, depth hover facts, and execution tape.
2. **Order ticket:** submit a limit order, read the exact integer-tick notional and risk bounds,
   then open its journal-backed lifecycle report.
3. **Match visualizer:** use an aggressive IOC or Large Buy Sweep to see price levels, individual
   fills, VWAP, and evidence sequences.
4. **Modify/cancel:** use `−1` on a live order to demonstrate same-price quantity-decrease
   priority retention, then cancel through direct node lookup.
5. **Failure Lab:** arm Drop Next Delta. The log shows the dropped sequence, detected gap,
   snapshot application, and recovery while the engine checksum stays authoritative.
6. **Engine X-Ray:** inspect the real best-price level, head/tail, current FIFO nodes, linked
   neighbors, price index, direct order-index size, and complexity claims.
7. **Recovery:** create a snapshot, let the market continue, then recover. PASS requires identical
   later event output, invariants, sequence, and final checksum.
8. **Replay:** use first/previous/play/next/last, change speed, jump to a command position, and
   filter real order/trade/cancel/risk evidence.
9. **Performance:** run an actual core benchmark, inspect the histogram/environment/memory facts,
   then run again for a descriptive history comparison.
10. **Risk & Surveillance:** inspect configured thresholds and observed rejection values, compare
    normal versus thin liquidity under the same seed, and run the evidence-grounded analyst.

## Keyboard map

- `⌘K` / `Ctrl-K`: command palette
- `Space`: pause or resume the simulation
- `R`: replay
- `P`: performance
- `E`: Engine X-Ray
- `Esc`: close palette or lifecycle inspector

No keyboard shortcut submits, modifies, or cancels an order.

## Demonstrating deterministic rejection semantics

- **FOK:** set a buy limit below best ask and choose FOK. Lifecycle evidence reports requested
  versus eligible quantity and confirms no mutation occurred.
- **Post-only:** choose a price crossing the opposing best. Evidence reports both prices.
- **Risk:** exceed max order quantity. The risk console and lifecycle show rule, observed value,
  and threshold.
- **IOC partial:** after reset, the seeded best level has finite quantity. Submit more than that
  at exactly the best price to execute the eligible quantity and cancel the remainder.

The optional external reference-price adapter was intentionally omitted from this pass. The
offline fixtures are explicitly labeled, deterministic, reproducible, and always available;
adding an unreliable network dependency would weaken the default demo. The adapter boundary is
straightforward because reference prices are isolated in `domain/instruments.py` and are used only
when a new simulation session is seeded.
