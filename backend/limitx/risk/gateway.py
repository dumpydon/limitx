from __future__ import annotations

from dataclasses import dataclass, field

from limitx.domain.enums import RejectReason, Side
from limitx.domain.order import Order
from limitx.engine.order_book import OrderBook


@dataclass(frozen=True, slots=True)
class RiskLimits:
    max_order_quantity: int = 25_000
    max_notional_ticks: int = 2_000_000_000
    max_live_orders: int = 2_000
    max_position: int = 100_000
    max_absolute_exposure_ticks: int = 5_000_000_000
    price_collar_bps: int = 2_000
    enabled_symbols: frozenset[str] = frozenset({"BTC-USD", "ETH-USD", "AAPL", "MSFT"})


@dataclass(slots=True)
class RiskState:
    positions: dict[tuple[str, str], int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RiskDecision:
    accepted: bool
    reason: RejectReason | None = None
    detail: str = ""
    observed: int | None = None
    threshold: int | None = None


class RiskGateway:
    def __init__(self, limits: RiskLimits | None = None) -> None:
        self.limits = limits or RiskLimits()
        self.state = RiskState()

    def check(self, order: Order, book: OrderBook) -> RiskDecision:
        limits = self.limits
        if order.symbol not in limits.enabled_symbols:
            return RiskDecision(False, RejectReason.RISK_SYMBOL_DISABLED, "symbol is disabled")
        if order.quantity > limits.max_order_quantity:
            return RiskDecision(
                False,
                RejectReason.RISK_MAX_ORDER_QUANTITY,
                "order quantity exceeds configured maximum",
                order.quantity,
                limits.max_order_quantity,
            )
        reference_price = order.price_ticks
        if reference_price is None:
            reference_price = book.best_ask if order.side is Side.BUY else book.best_bid
        if reference_price is None:
            reference_price = 0
        notional = reference_price * order.quantity
        if notional > limits.max_notional_ticks:
            return RiskDecision(
                False,
                RejectReason.RISK_MAX_NOTIONAL,
                "single-order notional exceeds configured maximum",
                notional,
                limits.max_notional_ticks,
            )
        live_count = book.live_order_count(order.account_id)
        if live_count >= limits.max_live_orders:
            return RiskDecision(
                False,
                RejectReason.RISK_MAX_LIVE_ORDERS,
                "account live-order count reached configured maximum",
                live_count,
                limits.max_live_orders,
            )
        current_position = self.state.positions.get((order.account_id, order.symbol), 0)
        signed_quantity = order.quantity if order.side is Side.BUY else -order.quantity
        if abs(current_position + signed_quantity) > limits.max_position:
            return RiskDecision(
                False,
                RejectReason.RISK_MAX_POSITION,
                "projected position exceeds configured maximum",
                abs(current_position + signed_quantity),
                limits.max_position,
            )
        if (
            abs((current_position + signed_quantity) * reference_price)
            > limits.max_absolute_exposure_ticks
        ):
            return RiskDecision(
                False,
                RejectReason.RISK_MAX_EXPOSURE,
                "projected absolute exposure exceeds configured maximum",
                abs((current_position + signed_quantity) * reference_price),
                limits.max_absolute_exposure_ticks,
            )
        if (
            order.price_ticks is not None
            and book.best_bid is not None
            and book.best_ask is not None
        ):
            mid = (book.best_bid + book.best_ask) // 2
            distance_bps = abs(order.price_ticks - mid) * 10_000 // max(mid, 1)
            if distance_bps > limits.price_collar_bps:
                return RiskDecision(
                    False,
                    RejectReason.RISK_PRICE_COLLAR,
                    "order price is outside the configured midpoint collar",
                    distance_bps,
                    limits.price_collar_bps,
                )
        return RiskDecision(True)

    def apply_trade(self, trade: dict[str, object]) -> None:
        symbol = str(trade.get("symbol", ""))
        quantity = int(str(trade["quantity"]))
        taker_side = Side(str(trade["aggressor_side"]))
        maker_key = (str(trade["maker_account_id"]), symbol)
        taker_key = (str(trade["taker_account_id"]), symbol)
        taker_delta = quantity if taker_side is Side.BUY else -quantity
        self.state.positions[taker_key] = self.state.positions.get(taker_key, 0) + taker_delta
        self.state.positions[maker_key] = self.state.positions.get(maker_key, 0) - taker_delta
