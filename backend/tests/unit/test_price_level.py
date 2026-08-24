from limitx.domain.enums import OrderType, Side
from limitx.domain.order import Order
from limitx.engine.linked_orders import OrderNode
from limitx.engine.price_level import PriceLevel


def node(order_id: str, quantity: int) -> OrderNode:
    return OrderNode(Order(order_id, "BTC-USD", order_id, Side.BUY, OrderType.LIMIT, quantity, 100))


def test_linked_level_arbitrary_removal_preserves_fifo():
    level = PriceLevel(100)
    first, middle, last = node("1", 2), node("2", 3), node("3", 4)
    for item in (first, middle, last):
        level.append(item)
    level.remove(middle)
    assert [item.order.order_id for item in level] == ["1", "3"]
    assert first.next is last and last.previous is first
    assert level.total_quantity == 6
    assert level.order_count == 2
