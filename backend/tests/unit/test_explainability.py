from limitx.analytics.explain import explain_order
from limitx.analytics.surveillance import SurveillanceEngine
from limitx.domain.commands import NewOrder
from limitx.domain.enums import OrderType, Side, TimeInForce
from limitx.domain.order import Order
from limitx.engine.order_book import OrderBook
from limitx.replay.journal import EventJournal


def submit(book: OrderBook, journal: EventJournal, order: Order) -> None:
    command = NewOrder(order)
    journal.record(command, book.process(command))


def test_explanations_use_fok_and_ioc_engine_facts(make_order):
    book = OrderBook("BTC-USD")
    journal = EventJournal("explain")
    submit(book, journal, make_order("ask", Side.SELL, 4, 101))
    fok = make_order("fok", Side.BUY, 5, 101, tif=TimeInForce.FOK)
    submit(book, journal, fok)
    explanation = explain_order(book, journal, "fok")
    assert explanation is not None
    assert "requested 5" in explanation["explanation"]
    assert "only 4" in explanation["explanation"]

    ioc = make_order("ioc", Side.BUY, 5, 101, tif=TimeInForce.IOC)
    submit(book, journal, ioc)
    explanation = explain_order(book, journal, "ioc")
    assert explanation is not None
    assert "unfilled 1-unit remainder was cancelled" in explanation["explanation"]
    assert all(
        item["evidence_id"].startswith(("event:", "command:")) for item in explanation["pipeline"]
    )


def test_large_sweep_surveillance_cites_trade_evidence(make_order):
    book = OrderBook("BTC-USD")
    for index, price in enumerate((101, 102, 103), 1):
        book.submit(make_order(f"ask-{index}", Side.SELL, 50, price))
    market = Order(
        "sweep",
        "BTC-USD",
        "whale",
        Side.BUY,
        OrderType.MARKET,
        150,
        None,
        TimeInForce.IOC,
    )
    book.submit(market)
    alerts = SurveillanceEngine().scan(book.events)
    sweep = next(alert for alert in alerts if alert.rule == "LARGE_SWEEP")
    assert len(sweep.evidence_ids) == 3
    assert "150 units" in sweep.explanation
