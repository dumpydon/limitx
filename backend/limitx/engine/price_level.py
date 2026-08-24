from __future__ import annotations

from collections.abc import Iterator

from limitx.engine.linked_orders import OrderNode


class PriceLevel:
    __slots__ = ("price", "total_quantity", "order_count", "head", "tail")

    def __init__(self, price: int) -> None:
        self.price = price
        self.total_quantity = 0
        self.order_count = 0
        self.head: OrderNode | None = None
        self.tail: OrderNode | None = None

    def append(self, node: OrderNode) -> None:
        if node.level is not None:
            raise ValueError("order node already belongs to a price level")
        node.level = self
        node.previous = self.tail
        node.next = None
        if self.tail is None:
            self.head = node
        else:
            self.tail.next = node
        self.tail = node
        self.order_count += 1
        self.total_quantity += node.order.remaining_qty

    def remove(self, node: OrderNode) -> None:
        if node.level is not self:
            raise ValueError("order node does not belong to this price level")
        if node.previous is None:
            self.head = node.next
        else:
            node.previous.next = node.next
        if node.next is None:
            self.tail = node.previous
        else:
            node.next.previous = node.previous
        self.order_count -= 1
        self.total_quantity -= node.order.remaining_qty
        node.previous = None
        node.next = None
        node.level = None

    def consume(self, node: OrderNode, quantity: int) -> None:
        if node.level is not self or quantity <= 0 or quantity > node.order.remaining_qty:
            raise ValueError("invalid level consumption")
        self.total_quantity -= quantity

    @property
    def is_empty(self) -> bool:
        return self.order_count == 0

    def __iter__(self) -> Iterator[OrderNode]:
        current = self.head
        while current is not None:
            yield current
            current = current.next
