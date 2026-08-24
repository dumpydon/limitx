from limitx.simulation.engine import MarketSimulation


def test_seed_reproduces_event_stream():
    first = MarketSimulation(seed=42, scenario="normal")
    second = MarketSimulation(seed=42, scenario="normal")
    assert first.run(100).as_dict() == second.run(100).as_dict()
    assert [event.as_dict() for event in first.book.events] == [
        event.as_dict() for event in second.book.events
    ]


def test_all_market_regimes_smoke():
    for scenario in ("thin_liquidity", "cancel_storm", "flash_selloff"):
        simulation = MarketSimulation(seed=7, scenario=scenario)
        simulation.run(40)
        simulation.book.assert_invariants()
