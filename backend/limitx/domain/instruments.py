from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Instrument:
    symbol: str
    display_name: str
    reference_price_ticks: int
    tick_size: str = "0.01"
    quantity_unit: str = "units"
    provenance: str = "LIMIT_X_DETERMINISTIC_FIXTURE"


INSTRUMENTS: dict[str, Instrument] = {
    "BTC-USD": Instrument("BTC-USD", "Bitcoin / US Dollar", 6_784_200, quantity_unit="units"),
    "ETH-USD": Instrument("ETH-USD", "Ether / US Dollar", 384_200, quantity_unit="units"),
    "AAPL": Instrument("AAPL", "Apple Inc. simulation", 23_475, quantity_unit="shares"),
    "MSFT": Instrument("MSFT", "Microsoft Corp. simulation", 41_885, quantity_unit="shares"),
}
