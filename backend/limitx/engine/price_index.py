from __future__ import annotations

from collections.abc import Iterator

from sortedcontainers import SortedDict

from limitx.domain.enums import Side
from limitx.engine.price_level import PriceLevel


class PriceIndex:
    """Ordered price-level map. SortedDict keeps tree-like index work isolated."""

    __slots__ = ("side", "_levels")

    def __init__(self, side: Side) -> None:
        self.side = side
        self._levels: SortedDict[int, PriceLevel] = SortedDict()

    def get(self, price: int) -> PriceLevel | None:
        return self._levels.get(price)

    def get_or_create(self, price: int) -> PriceLevel:
        level = self._levels.get(price)
        if level is None:
            level = PriceLevel(price)
            self._levels[price] = level
        return level

    def remove(self, price: int) -> None:
        del self._levels[price]

    @property
    def best(self) -> PriceLevel | None:
        if not self._levels:
            return None
        position = -1 if self.side is Side.BUY else 0
        return self._levels.peekitem(position)[1]

    def levels_best_first(self) -> Iterator[PriceLevel]:
        values = self._levels.values()
        if self.side is Side.BUY:
            yield from reversed(values)
        else:
            yield from values

    def __len__(self) -> int:
        return len(self._levels)
