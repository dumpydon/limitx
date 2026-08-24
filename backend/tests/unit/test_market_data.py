from limitx.domain.enums import Side
from limitx.engine.order_book import OrderBook
from limitx.market_data.projector import MarketDataProjector, SequenceGuard


def test_projection_and_sequence_gap_recovery(make_order):
    book = OrderBook("BTC-USD")
    projector = MarketDataProjector(book)
    projector.project(book.submit(make_order("B1", Side.BUY, 5, 100)))
    snapshot = projector.snapshot()
    assert snapshot["payload"]["l1"]["best_bid"] == 100
    guard = SequenceGuard()
    guard.accept_snapshot(10)
    assert guard.accept_delta(11) == "APPLIED"
    assert guard.accept_delta(11) == "DUPLICATE_OR_OLD"
    assert guard.accept_delta(13) == "GAP"
    assert guard.accept_delta(14) == "RESYNC_REQUIRED"
