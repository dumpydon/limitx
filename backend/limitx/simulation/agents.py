from __future__ import annotations

import random
from dataclasses import dataclass

from limitx.domain.commands import NewOrder
from limitx.domain.enums import OrderType, Side, TimeInForce
from limitx.domain.order import Order
from limitx.engine.order_book import OrderBook


@dataclass(slots=True)
class AgentContext:
    rng: random.Random
    symbol: str
    step: int
    center_ticks: int
    id_counter: int

    def order_id(self, prefix: str) -> str:
        return f"{prefix}-{self.id_counter:09d}"


class MarketAgent:
    account_id = "agent"
    prefix = "A"

    def command(self, context: AgentContext, book: OrderBook) -> NewOrder:
        raise NotImplementedError

    def _order(
        self,
        context: AgentContext,
        side: Side,
        quantity: int,
        order_type: OrderType,
        price: int | None,
        tif: TimeInForce,
    ) -> NewOrder:
        return NewOrder(
            Order(
                order_id=context.order_id(self.prefix),
                symbol=context.symbol,
                account_id=self.account_id,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price_ticks=price,
                time_in_force=tif,
            )
        )


class NoiseTrader(MarketAgent):
    account_id = "noise"
    prefix = "N"

    def command(self, context: AgentContext, book: OrderBook) -> NewOrder:
        side = context.rng.choice([Side.BUY, Side.SELL])
        offset = context.rng.randint(2, 18)
        price = context.center_ticks - offset if side is Side.BUY else context.center_ticks + offset
        return self._order(
            context, side, context.rng.randint(1, 35), OrderType.LIMIT, price, TimeInForce.GTC
        )


class MarketMaker(MarketAgent):
    account_id = "maker"
    prefix = "MM"

    def command(self, context: AgentContext, book: OrderBook) -> NewOrder:
        side = Side.BUY if context.step % 2 == 0 else Side.SELL
        half_spread = context.rng.randint(2, 5)
        price = (
            context.center_ticks - half_spread
            if side is Side.BUY
            else context.center_ticks + half_spread
        )
        return self._order(
            context,
            side,
            context.rng.randint(20, 70),
            OrderType.LIMIT,
            price,
            TimeInForce.POST_ONLY,
        )


class MomentumAgent(MarketAgent):
    account_id = "momentum"
    prefix = "MO"

    def command(self, context: AgentContext, book: OrderBook) -> NewOrder:
        recent = book.trades[-4:]
        direction = Side.BUY
        if len(recent) >= 2 and int(recent[-1]["price_ticks"]) < int(recent[0]["price_ticks"]):
            direction = Side.SELL
        elif not recent:
            direction = context.rng.choice([Side.BUY, Side.SELL])
        return self._order(
            context,
            direction,
            context.rng.randint(2, 20),
            OrderType.MARKET,
            None,
            TimeInForce.IOC,
        )


class LiquidityTaker(MarketAgent):
    account_id = "taker"
    prefix = "LT"

    def command(self, context: AgentContext, book: OrderBook) -> NewOrder:
        return self._order(
            context,
            context.rng.choice([Side.BUY, Side.SELL]),
            context.rng.randint(5, 45),
            OrderType.MARKET,
            None,
            TimeInForce.IOC,
        )


class WhaleAgent(MarketAgent):
    account_id = "whale"
    prefix = "WH"

    def command(self, context: AgentContext, book: OrderBook) -> NewOrder:
        return self._order(
            context,
            Side.SELL if context.step % 3 else Side.BUY,
            context.rng.randint(120, 320),
            OrderType.MARKET,
            None,
            TimeInForce.IOC,
        )
