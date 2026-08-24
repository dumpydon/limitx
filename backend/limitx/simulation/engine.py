from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from limitx.domain.commands import CancelOrder, Command, NewOrder
from limitx.domain.enums import OrderType, Side, TimeInForce
from limitx.domain.order import Order
from limitx.engine.order_book import OrderBook
from limitx.replay.journal import EventJournal
from limitx.simulation.agents import (
    AgentContext,
    LiquidityTaker,
    MarketAgent,
    MarketMaker,
    MomentumAgent,
    NoiseTrader,
    WhaleAgent,
)
from limitx.simulation.scenarios import SCENARIOS, Scenario


@dataclass(frozen=True, slots=True)
class SimulationResult:
    seed: int
    scenario: str
    operations: int
    trades: int
    checksum: str
    event_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "scenario": self.scenario,
            "operations": self.operations,
            "trades": self.trades,
            "checksum": self.checksum,
            "event_count": self.event_count,
        }


class MarketSimulation:
    def __init__(
        self,
        symbol: str = "BTC-USD",
        *,
        seed: int = 42,
        scenario: str = "normal",
        center_ticks: int = 10_000_000,
        book: OrderBook | None = None,
        journal: EventJournal | None = None,
    ) -> None:
        if scenario not in SCENARIOS:
            raise ValueError(f"unknown scenario: {scenario}")
        self.symbol = symbol
        self.seed = seed
        self.rng = random.Random(seed)
        self.scenario_key = scenario
        self.scenario: Scenario = SCENARIOS[scenario]
        self.center_ticks = center_ticks
        self.book = book or OrderBook(symbol)
        self.journal = journal or EventJournal(f"sim-{scenario}-{seed}")
        self.step_number = 0
        self.id_counter = 0
        self.agents: tuple[MarketAgent, ...] = (
            MarketMaker(),
            NoiseTrader(),
            MomentumAgent(),
            LiquidityTaker(),
            WhaleAgent(),
        )
        self.weights = (
            self.scenario.maker_weight,
            self.scenario.noise_weight,
            self.scenario.momentum_weight,
            self.scenario.taker_weight,
            self.scenario.whale_weight,
        )

    def _process(self, command: Command) -> None:
        events = self.book.process(command)
        self.journal.record(command, events)

    def seed_book(self, levels: int = 12) -> None:
        for offset in range(levels, 0, -1):
            for side in (Side.BUY, Side.SELL):
                self.id_counter += 1
                price = (
                    self.center_ticks - offset if side is Side.BUY else self.center_ticks + offset
                )
                command = NewOrder(
                    Order(
                        order_id=f"SEED-{self.id_counter:09d}",
                        symbol=self.symbol,
                        account_id=f"seed-{side.value.lower()}-{offset}",
                        side=side,
                        order_type=OrderType.LIMIT,
                        time_in_force=TimeInForce.GTC,
                        price_ticks=price,
                        quantity=35 + (levels - offset) * 5,
                    )
                )
                self._process(command)

    def step(self) -> Command:
        command = self.next_command()
        self._process(command)
        return command

    def next_command(self) -> Command:
        self.step_number += 1
        self.center_ticks = max(10, self.center_ticks + self.scenario.center_drift)
        live = list(self.book.live_orders)
        if live and self.rng.random() < self.scenario.cancel_probability:
            order_id = self.rng.choice(live)
            node = self.book.live_orders[order_id]
            command: Command = CancelOrder(self.symbol, order_id, node.order.account_id)
        else:
            self.id_counter += 1
            agent = self.rng.choices(self.agents, weights=self.weights, k=1)[0]
            context = AgentContext(
                rng=self.rng,
                symbol=self.symbol,
                step=self.step_number,
                center_ticks=self.center_ticks,
                id_counter=self.id_counter,
            )
            command = agent.command(context, self.book)
            if (
                isinstance(command, NewOrder)
                and command.order.order_type is OrderType.MARKET
                and self.scenario.forced_aggressor_side is not None
            ):
                command.order.side = self.scenario.forced_aggressor_side
        return command

    def run(self, operations: int, *, seed_liquidity: bool = True) -> SimulationResult:
        if seed_liquidity and not self.book.orders:
            self.seed_book()
        trades_before = len(self.book.trades)
        for _ in range(operations):
            self.step()
        self.book.assert_invariants()
        self.journal.set_checksum(self.symbol, self.book.checksum())
        return SimulationResult(
            seed=self.seed,
            scenario=self.scenario_key,
            operations=operations,
            trades=len(self.book.trades) - trades_before,
            checksum=self.book.checksum(),
            event_count=len(self.book.events),
        )
