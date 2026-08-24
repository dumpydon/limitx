from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from limitx.ai.analyst import ReplayAnalyst
from limitx.analytics.exports import export_artifacts
from limitx.analytics.microstructure import calculate_metrics
from limitx.api.schemas import (
    AnalystRequest,
    BenchmarkRequest,
    ModifyRequest,
    OrderRequest,
    SimulationRequest,
)
from limitx.benchmarks.runner import run_benchmark
from limitx.domain.commands import CancelOrder, ModifyOrder, NewOrder
from limitx.domain.order import Order
from limitx.engine.gateway import EngineGateway
from limitx.replay.replay import ReplaySession
from limitx.simulation.engine import MarketSimulation
from limitx.simulation.scenarios import SCENARIOS

gateway = EngineGateway()
simulation_tasks: dict[str, asyncio.Task[None]] = {}
last_benchmark: dict[str, object] | None = None
simulation_state: dict[str, dict[str, Any]] = {
    symbol: {"status": "IDLE", "scenario": None, "seed": None, "operations": 0, "speed": 1}
    for symbol in gateway.SYMBOLS
}


async def _run_simulation(request: SimulationRequest) -> None:
    symbol = request.symbol
    simulation = MarketSimulation(
        symbol=symbol,
        seed=request.seed,
        scenario=request.scenario,
        book=gateway.books[symbol],
    )
    simulation_state[symbol].update(
        status="RUNNING",
        scenario=request.scenario,
        seed=request.seed,
        operations=0,
        speed=request.speed,
    )
    delay = 0 if request.speed >= 50 else 0.03 / request.speed
    try:
        for index in range(request.operations):
            while simulation_state[symbol]["status"] == "PAUSED":
                await asyncio.sleep(0.05)
            command = simulation.next_command()
            await gateway.process(command)
            simulation_state[symbol]["operations"] = index + 1
            if delay:
                await asyncio.sleep(delay)
            elif index % 100 == 0:
                await asyncio.sleep(0)
        simulation_state[symbol]["status"] = "COMPLETE"
    except asyncio.CancelledError:
        simulation_state[symbol]["status"] = "IDLE"
        raise


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    gateway.start()
    for symbol in gateway.SYMBOLS:
        gateway.seed(symbol, 10_000_000 if "USD" in symbol else 20_000)
    yield
    for task in simulation_tasks.values():
        task.cancel()
    await gateway.stop()


app = FastAPI(
    title="Limit X API",
    version="0.1.0",
    description="Deterministic simulated exchange matching engine; never routes real orders.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["content-type"],
)


def _require_symbol(symbol: str) -> None:
    if symbol not in gateway.books:
        raise HTTPException(404, "unknown symbol")


@app.get("/health")
async def health() -> dict[str, object]:
    return {"status": "ok", "service": "limitx", "real_trading": False}


@app.get("/api/symbols")
async def symbols() -> dict[str, object]:
    return {"symbols": list(gateway.SYMBOLS)}


@app.get("/api/book/{symbol}")
async def book(symbol: str) -> dict[str, Any]:
    _require_symbol(symbol)
    return gateway.projectors[symbol].snapshot()


@app.get("/api/book/{symbol}/depth")
async def depth(symbol: str, levels: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
    _require_symbol(symbol)
    return {
        "symbol": symbol,
        "sequence": gateway.books[symbol].sequencer.value,
        **gateway.books[symbol].depth(levels),
    }


@app.get("/api/trades/{symbol}")
async def trades(symbol: str, limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
    _require_symbol(symbol)
    return {"symbol": symbol, "trades": gateway.books[symbol].trades[-limit:][::-1]}


@app.post("/api/orders")
async def submit_order(request: OrderRequest) -> dict[str, Any]:
    _require_symbol(request.symbol)
    order = Order(
        order_id=request.order_id,
        symbol=request.symbol,
        account_id=request.account_id,
        side=request.side,
        order_type=request.order_type,
        time_in_force=request.time_in_force,
        price_ticks=request.price_ticks,
        quantity=request.quantity,
    )
    events = await gateway.process(NewOrder(order))
    return {"events": [event.as_dict() for event in events], "order": order.as_dict()}


@app.delete("/api/orders/{order_id}")
async def cancel_order(
    order_id: str,
    symbol: str = Query(...),
    account_id: str | None = Query(default=None),
) -> dict[str, Any]:
    _require_symbol(symbol)
    events = await gateway.process(CancelOrder(symbol, order_id, account_id))
    return {"events": [event.as_dict() for event in events]}


@app.patch("/api/orders/{order_id}")
async def modify_order(order_id: str, request: ModifyRequest) -> dict[str, Any]:
    _require_symbol(request.symbol)
    events = await gateway.process(
        ModifyOrder(
            request.symbol,
            order_id,
            request.new_quantity,
            request.new_price_ticks,
            request.account_id,
        )
    )
    return {"events": [event.as_dict() for event in events]}


@app.get("/api/orders/live/{symbol}")
async def live_orders(symbol: str, account_id: str | None = Query(default=None)) -> dict[str, Any]:
    _require_symbol(symbol)
    return {
        "orders": [order.as_dict() for order in gateway.books[symbol].iter_live_orders(account_id)]
    }


@app.post("/api/simulation/start")
async def simulation_start(request: SimulationRequest) -> dict[str, Any]:
    _require_symbol(request.symbol)
    if request.scenario not in SCENARIOS:
        raise HTTPException(422, "unknown scenario")
    existing = simulation_tasks.get(request.symbol)
    if existing and not existing.done():
        existing.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await existing
    if request.reset:
        gateway.reset(request.symbol)
        gateway.seed(request.symbol, 10_000_000 if "USD" in request.symbol else 20_000)
    task = asyncio.create_task(_run_simulation(request))
    simulation_tasks[request.symbol] = task
    return {"state": simulation_state[request.symbol]}


@app.post("/api/simulation/pause")
async def simulation_pause(symbol: str = Query("BTC-USD")) -> dict[str, Any]:
    _require_symbol(symbol)
    simulation_state[symbol]["status"] = "PAUSED"
    return {"state": simulation_state[symbol]}


@app.post("/api/simulation/resume")
async def simulation_resume(symbol: str = Query("BTC-USD")) -> dict[str, Any]:
    _require_symbol(symbol)
    simulation_state[symbol]["status"] = "RUNNING"
    return {"state": simulation_state[symbol]}


@app.post("/api/simulation/reset")
async def simulation_reset(symbol: str = Query("BTC-USD")) -> dict[str, Any]:
    _require_symbol(symbol)
    task = simulation_tasks.get(symbol)
    if task and not task.done():
        task.cancel()
    gateway.reset(symbol)
    gateway.seed(symbol, 10_000_000 if "USD" in symbol else 20_000)
    simulation_state[symbol].update(status="IDLE", scenario=None, seed=None, operations=0)
    return {"state": simulation_state[symbol], "snapshot": gateway.projectors[symbol].snapshot()}


@app.post("/api/scenarios/{scenario}")
async def choose_scenario(scenario: str, request: SimulationRequest) -> dict[str, Any]:
    request.scenario = scenario
    return await simulation_start(request)


@app.get("/api/simulation/state/{symbol}")
async def get_simulation_state(symbol: str) -> dict[str, Any]:
    _require_symbol(symbol)
    return {"state": simulation_state[symbol]}


@app.get("/api/metrics/{symbol}")
async def metrics(symbol: str) -> dict[str, Any]:
    _require_symbol(symbol)
    return {
        "symbol": symbol,
        "metrics": calculate_metrics(gateway.books[symbol]),
        "surveillance_alerts": gateway.alerts[symbol],
    }


@app.get("/api/system/{symbol}")
async def system(symbol: str) -> dict[str, Any]:
    _require_symbol(symbol)
    return gateway.system_state(symbol)


@app.post("/api/benchmarks")
async def benchmark(request: BenchmarkRequest) -> dict[str, object]:
    global last_benchmark
    try:
        result = await asyncio.to_thread(
            run_benchmark,
            scenario=request.scenario,
            operations=request.operations,
            seed=request.seed,
            runs=request.runs,
        )
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    last_benchmark = result.as_dict()
    return last_benchmark


@app.get("/api/replay/sessions")
async def replay_sessions() -> dict[str, Any]:
    for symbol, journal in gateway.journals.items():
        journal.set_checksum(symbol, gateway.books[symbol].checksum())
    return {
        "sessions": [
            {
                "session_id": journal.session_id,
                "symbol": symbol,
                "commands": len(journal.entries),
                "checksum": journal.final_checksums.get(symbol),
            }
            for symbol, journal in gateway.journals.items()
        ]
    }


@app.post("/api/replay/load")
async def replay_load(
    symbol: str = Query("BTC-USD"), position: int | None = None
) -> dict[str, Any]:
    _require_symbol(symbol)
    gateway.journals[symbol].set_checksum(symbol, gateway.books[symbol].checksum())
    replay = ReplaySession(gateway.journals[symbol])
    target = len(gateway.journals[symbol].entries) if position is None else position
    try:
        books = replay.jump(target)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    replay_book = books.get(symbol)
    return {
        "session_id": gateway.journals[symbol].session_id,
        "position": replay.position,
        "total": len(gateway.journals[symbol].entries),
        "snapshot": replay_book.snapshot() if replay_book else None,
        "latest_entry": (gateway.journals[symbol].entries[target - 1].events if target else None),
    }


@app.post("/api/analyst")
async def analyst(request: AnalystRequest) -> dict[str, Any]:
    _require_symbol(request.symbol)
    evidence = [event.as_dict() for event in gateway.books[request.symbol].events[-500:]]
    return ReplayAnalyst().analyze(request.question, evidence).as_dict()


@app.post("/api/export/{symbol}")
async def export_session(symbol: str) -> dict[str, Any]:
    _require_symbol(symbol)
    gateway.journals[symbol].set_checksum(symbol, gateway.books[symbol].checksum())
    export_root = Path("data").resolve() / f"limitx-{symbol.replace('/', '-')}"
    files = export_artifacts(
        export_root,
        gateway.books[symbol],
        gateway.journals[symbol],
        last_benchmark,
    )
    return {
        "files": [path.name for path in files],
        "commands": len(gateway.journals[symbol].entries),
    }


@app.websocket("/ws/market/{symbol}")
async def websocket_market(websocket: WebSocket, symbol: str) -> None:
    if symbol not in gateway.books:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    queue = gateway.broker.subscribe(symbol)
    await websocket.send_json(gateway.projectors[symbol].snapshot())
    try:
        while True:
            message = await queue.get()
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass
    finally:
        gateway.broker.unsubscribe(symbol, queue)
