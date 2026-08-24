from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from limitx.domain.enums import OrderType, Side, TimeInForce


class OrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(min_length=1, max_length=80)
    symbol: str = Field(min_length=1, max_length=20)
    account_id: str = Field(default="demo-user", min_length=1, max_length=80)
    side: Side
    order_type: OrderType
    quantity: int = Field(gt=0, le=1_000_000)
    price_ticks: int | None = Field(default=None, gt=0)
    time_in_force: TimeInForce = TimeInForce.GTC

    @model_validator(mode="after")
    def validate_semantics(self) -> OrderRequest:
        if self.order_type is OrderType.LIMIT and self.price_ticks is None:
            raise ValueError("limit orders require price_ticks")
        if self.order_type is OrderType.MARKET and self.price_ticks is not None:
            raise ValueError("market orders must not include price_ticks")
        if self.order_type is OrderType.MARKET and self.time_in_force not in {
            TimeInForce.IOC,
            TimeInForce.FOK,
        }:
            raise ValueError("market orders require IOC or FOK")
        return self


class ModifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str
    new_quantity: int = Field(gt=0, le=1_000_000)
    new_price_ticks: int | None = Field(default=None, gt=0)
    account_id: str | None = None


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str = "BTC-USD"
    scenario: str = "normal"
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    operations: int = Field(default=250, ge=1, le=50_000)
    speed: float = Field(default=1, gt=0, le=100)
    reset: bool = True


class BenchmarkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario: str = "mixed"
    operations: int = Field(default=10_000, ge=100, le=100_000)
    seed: int = 42
    runs: int = Field(default=1, ge=1, le=5)


class AnalystRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str = "BTC-USD"
    question: str = Field(min_length=1, max_length=500)
