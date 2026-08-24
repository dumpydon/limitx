from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from limitx.domain.order import Order

if TYPE_CHECKING:
    from limitx.engine.price_level import PriceLevel


@dataclass(slots=True)
class OrderNode:
    order: Order
    level: PriceLevel | None = None
    previous: OrderNode | None = None
    next: OrderNode | None = None
