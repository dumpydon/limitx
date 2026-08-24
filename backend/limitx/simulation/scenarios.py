from __future__ import annotations

from dataclasses import dataclass

from limitx.domain.enums import Side


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
    description: str = "Deterministic synthetic order flow."
    expected_characteristics: str = "Balanced liquidity and mixed order flow."
    forced_aggressor_side: Side | None = None


SCENARIOS: dict[str, Scenario] = {
    "normal": Scenario(
        "Normal Market",
        40,
        35,
        8,
        15,
        2,
        0.18,
        description="Balanced makers, noise flow, and periodic liquidity taking.",
        expected_characteristics="Stable depth with modest spread and two-sided executions.",
    ),
    "thin_liquidity": Scenario(
        "Thin Liquidity",
        12,
        28,
        18,
        34,
        8,
        0.35,
        description="Reduced maker participation with more aggressive consumption.",
        expected_characteristics="Lower depth, wider spreads, and higher slippage sensitivity.",
    ),
    "high_volatility": Scenario(
        "Volatility Burst",
        20,
        20,
        28,
        25,
        7,
        0.22,
        2,
        description="Momentum and taker activity dominate while the reference center drifts.",
        expected_characteristics="Faster price movement and unstable top-of-book depth.",
    ),
    "cancel_storm": Scenario(
        "Cancel Storm",
        48,
        22,
        4,
        5,
        1,
        0.85,
        description="A synthetic cancellation-dominant data-structure stress profile.",
        expected_characteristics="High cancel/add ratio and frequent arbitrary node unlinking.",
    ),
    "liquidity_shock": Scenario(
        "Liquidity Shock",
        15,
        15,
        10,
        25,
        35,
        0.45,
        -2,
        description="Large orders meet rapidly disappearing displayed liquidity.",
        expected_characteristics="Depth loss, wider spread, and elevated price impact.",
    ),
    "large_market_sweep": Scenario(
        "Large Mixed Sweep",
        22,
        18,
        5,
        15,
        40,
        0.12,
        description="Whale orders periodically sweep several resting price levels.",
        expected_characteristics="Multi-level fills and visible VWAP/slippage paths.",
    ),
    "large_buy_sweep": Scenario(
        "Large Buy Sweep",
        22,
        18,
        5,
        15,
        40,
        0.12,
        description="Aggressive synthetic buy flow repeatedly consumes ask depth.",
        expected_characteristics="Ask-level sweeps and positive directional price impact.",
        forced_aggressor_side=Side.BUY,
    ),
    "large_sell_sweep": Scenario(
        "Large Sell Sweep",
        22,
        18,
        5,
        15,
        40,
        0.12,
        description="Aggressive synthetic sell flow repeatedly consumes bid depth.",
        expected_characteristics="Bid-level sweeps and negative directional price impact.",
        forced_aggressor_side=Side.SELL,
    ),
    "one_sided_flow": Scenario(
        "One-Sided Flow",
        20,
        20,
        35,
        20,
        5,
        0.15,
        1,
        description="Buy-side aggressors dominate a still-active two-sided book.",
        expected_characteristics="Positive order-flow imbalance and inventory pressure.",
        forced_aggressor_side=Side.BUY,
    ),
    "spread_compression": Scenario(
        "Spread Compression",
        65,
        25,
        3,
        6,
        1,
        0.25,
        description="Maker participation dominates and competes near the touch.",
        expected_characteristics="Dense near-touch liquidity and a compressed spread.",
    ),
    "flash_selloff": Scenario(
        "Flash Selloff",
        15,
        10,
        30,
        20,
        25,
        0.35,
        -4,
        description="Forced sell aggressors and negative center drift stress bid recovery.",
        expected_characteristics="Abrupt downside move, depleted bids, and wider spreads.",
        forced_aggressor_side=Side.SELL,
    ),
}
