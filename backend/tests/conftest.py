from __future__ import annotations

import pytest

from limitx.domain.enums import OrderType, Side, TimeInForce
from limitx.domain.order import Order


@pytest.fixture
def make_order():
    def factory(
        order_id: str,
        side: Side,
        quantity: int,
        price: int | None,
        *,
        account: str | None = None,
        order_type: OrderType = OrderType.LIMIT,
        tif: TimeInForce = TimeInForce.GTC,
        symbol: str = "BTC-USD",
    ) -> Order:
        return Order(
            order_id=order_id,
            symbol=symbol,
            account_id=account or order_id,
            side=side,
            order_type=order_type,
            time_in_force=tif,
            quantity=quantity,
            price_ticks=price,
        )

    return factory
