from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from limitx.domain.commands import CancelOrder, ModifyOrder, NewOrder
from limitx.domain.enums import OrderType, Side, TimeInForce
from limitx.domain.order import Order
from limitx.engine.order_book import OrderBook

operation_strategy = st.lists(
    st.tuples(
        st.integers(min_value=0, max_value=2),
        st.integers(min_value=0, max_value=25),
        st.sampled_from(list(Side)),
        st.integers(min_value=-2, max_value=30),
        st.integers(min_value=95, max_value=105),
        st.sampled_from(list(TimeInForce)),
        st.sampled_from(list(OrderType)),
        st.integers(min_value=0, max_value=4),
    ),
    min_size=1,
    max_size=70,
)


@settings(max_examples=120, deadline=None)
@given(operation_strategy)
def test_randomized_operations_preserve_book_invariants(operations):
    book = OrderBook("BTC-USD")
    ids: list[str] = []
    for index, (kind, target, side, quantity, price, tif, order_type, account) in enumerate(
        operations
    ):
        if kind == 0:
            order_id = f"O-{index}"
            ids.append(order_id)
            effective_tif = (
                tif
                if order_type is OrderType.LIMIT
                else (TimeInForce.FOK if tif is TimeInForce.FOK else TimeInForce.IOC)
            )
            book.process(
                NewOrder(
                    Order(
                        order_id,
                        "BTC-USD",
                        f"acct-{account}",
                        side,
                        order_type,
                        quantity,
                        price if order_type is OrderType.LIMIT else None,
                        effective_tif,
                    )
                )
            )
        elif kind == 1:
            order_id = ids[target % len(ids)] if ids else "missing"
            book.process(CancelOrder("BTC-USD", order_id))
        else:
            order_id = ids[target % len(ids)] if ids else "missing"
            book.process(ModifyOrder("BTC-USD", order_id, max(quantity, 1), price))
        book.assert_invariants()
