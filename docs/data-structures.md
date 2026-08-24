# Data structures

## Selected design

| Concern | Structure | Expected complexity |
|---|---|---:|
| Order ID lookup | `dict[order_id, OrderNode]` | O(1) expected |
| Cancel after lookup | Intrusive doubly linked node | O(1) |
| FIFO append | Price-level tail pointer | O(1) |
| Best bid/ask | `SortedDict.peekitem` | O(1) indexed endpoint |
| Existing level lookup | `SortedDict` | O(log P) |
| New/remove level | `SortedDict` | approximately O(log P) |
| Matching | Consumed orders/levels plus index work | O(K + L log P) |

`P` is active price levels, `K` consumed orders, and `L` removed levels. Python object and library
constants remain material; these are algorithmic expectations, not latency promises.

## Why two layers?

Price selection and FIFO order selection are different problems. `PriceIndex` owns sorted prices.
Each `PriceLevel` owns aggregate visible quantity, count, head, tail, and its linked FIFO. This
keeps arbitrary order removal out of price-selection code.

## Alternatives

- A plain list makes best-price lookup or insert expensive and encourages accidental scans.
- A deque has O(1) endpoints but not O(1) arbitrary middle unlink after order lookup.
- A heap finds one best price efficiently but arbitrary deletion needs tombstones/index repair;
  empty-level cleanup and bid/ask traversal become awkward.
- A balanced tree is the natural price index. `SortedDict` supplies that interface in Python and
  is isolated so a native tree can replace it.
- Lazy cancellation simplifies unlinking but leaves dead nodes and makes cancel-storm memory and
  latency less inspectable.

