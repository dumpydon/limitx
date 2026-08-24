from limitx.domain.enums import RejectReason, Side
from limitx.engine.order_book import OrderBook
from limitx.risk.gateway import RiskGateway, RiskLimits


def test_risk_limits_are_explicit(make_order):
    limits = RiskLimits(max_order_quantity=10, enabled_symbols=frozenset({"BTC-USD"}))
    gateway = RiskGateway(limits)
    book = OrderBook("BTC-USD")
    decision = gateway.check(make_order("B", Side.BUY, 11, 100), book)
    assert decision.reason is RejectReason.RISK_MAX_ORDER_QUANTITY

    disabled = OrderBook("ETH-USD")
    decision = gateway.check(make_order("E", Side.BUY, 1, 100, symbol="ETH-USD"), disabled)
    assert decision.reason is RejectReason.RISK_SYMBOL_DISABLED
