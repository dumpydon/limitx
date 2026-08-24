from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    maker_weight: int
    noise_weight: int
    momentum_weight: int
    taker_weight: int
    whale_weight: int
    cancel_probability: float
    center_drift: int = 0


SCENARIOS: dict[str, Scenario] = {
    "normal": Scenario("Normal Market", 40, 35, 8, 15, 2, 0.18),
    "thin_liquidity": Scenario("Thin Liquidity", 12, 28, 18, 34, 8, 0.35),
    "high_volatility": Scenario("High Volatility", 20, 20, 28, 25, 7, 0.22, 2),
    "cancel_storm": Scenario("Cancel Storm", 48, 22, 4, 5, 1, 0.85),
    "liquidity_shock": Scenario("Liquidity Shock", 15, 15, 10, 25, 35, 0.45, -2),
    "large_market_sweep": Scenario("Large Market Sweep", 22, 18, 5, 15, 40, 0.12),
    "one_sided_flow": Scenario("One-Sided Flow", 20, 20, 35, 20, 5, 0.15, 1),
    "spread_compression": Scenario("Spread Compression", 65, 25, 3, 6, 1, 0.25),
    "flash_selloff": Scenario("Flash Selloff", 15, 10, 30, 20, 25, 0.35, -4),
}
