from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from limitx.domain.enums import Side


@dataclass(slots=True)
class Position:
    quantity: int = 0
    average_entry_ticks: Fraction = Fraction(0)
    realized_pnl_ticks: Fraction = Fraction(0)
    cash_ticks: int = 0

    def apply(self, side: Side, price_ticks: int, quantity: int) -> None:
        signed = quantity if side is Side.BUY else -quantity
        if self.quantity == 0 or (self.quantity > 0) == (signed > 0):
            new_quantity = self.quantity + signed
            if new_quantity:
                total_cost = self.average_entry_ticks * abs(self.quantity) + price_ticks * quantity
                self.average_entry_ticks = total_cost / abs(new_quantity)
            self.quantity = new_quantity
        else:
            closing = min(abs(self.quantity), quantity)
            direction = 1 if self.quantity > 0 else -1
            self.realized_pnl_ticks += (
                direction * (price_ticks - self.average_entry_ticks) * closing
            )
            self.quantity += signed
            if self.quantity == 0:
                self.average_entry_ticks = Fraction(0)
            elif abs(signed) > closing:
                self.average_entry_ticks = Fraction(price_ticks)
        self.cash_ticks -= signed * price_ticks

    def as_dict(self, mark_ticks: int | None = None) -> dict[str, Any]:
        unrealized = (
            (Fraction(mark_ticks) - self.average_entry_ticks) * self.quantity
            if mark_ticks is not None
            else Fraction(0)
        )
        return {
            "position": self.quantity,
            "cash_ticks": self.cash_ticks,
            "average_entry_ticks": float(self.average_entry_ticks),
            "realized_pnl_ticks": float(self.realized_pnl_ticks),
            "unrealized_pnl_ticks": float(unrealized),
        }


class AccountLedger:
    def __init__(self) -> None:
        self.positions: dict[tuple[str, str], Position] = {}

    def apply_trade(self, symbol: str, trade: dict[str, Any]) -> None:
        quantity = int(trade["quantity"])
        price = int(trade["price_ticks"])
        taker_side = Side(str(trade["aggressor_side"]))
        taker = self.positions.setdefault((str(trade["taker_account_id"]), symbol), Position())
        maker = self.positions.setdefault((str(trade["maker_account_id"]), symbol), Position())
        taker.apply(taker_side, price, quantity)
        maker.apply(taker_side.opposite, price, quantity)

    def account(self, account_id: str, marks: dict[str, int | None]) -> dict[str, Any]:
        return {
            symbol: position.as_dict(marks.get(symbol))
            for (account, symbol), position in self.positions.items()
            if account == account_id
        }
