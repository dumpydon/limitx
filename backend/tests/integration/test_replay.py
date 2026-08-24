from pathlib import Path

from limitx.domain.commands import NewOrder
from limitx.domain.enums import OrderType, Side, TimeInForce
from limitx.domain.order import Order
from limitx.engine.gateway import EngineGateway
from limitx.replay.audit import audit
from limitx.replay.journal import EventJournal
from limitx.replay.replay import ReplaySession
from limitx.simulation.engine import MarketSimulation


def test_journal_export_replay_and_audit(tmp_path: Path):
    journal = EventJournal("integration")
    simulation = MarketSimulation(seed=19, scenario="normal", journal=journal)
    simulation.run(120)
    path = tmp_path / "session.jsonl"
    journal.export(path)

    loaded = EventJournal.load(path)
    result = ReplaySession(loaded).run()
    assert not result.divergences
    assert result.checksums == loaded.final_checksums
    assert audit(path)["valid"] is True


def test_gateway_risk_rejections_replay_identically():
    gateway = EngineGateway()
    order = Order(
        "too-large",
        "BTC-USD",
        "account",
        Side.BUY,
        OrderType.LIMIT,
        25_001,
        100,
        TimeInForce.GTC,
    )
    gateway.process_direct("BTC-USD", NewOrder(order))
    journal = gateway.journals["BTC-USD"]
    journal.set_checksum("BTC-USD", gateway.books["BTC-USD"].checksum())
    result = ReplaySession(journal).run()
    assert not result.divergences
