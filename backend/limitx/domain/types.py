from typing import NewType

OrderId = NewType("OrderId", str)
Symbol = NewType("Symbol", str)
AccountId = NewType("AccountId", str)
Price = NewType("Price", int)
Quantity = NewType("Quantity", int)
SequenceNumber = NewType("SequenceNumber", int)
Timestamp = NewType("Timestamp", int)
