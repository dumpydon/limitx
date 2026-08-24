from fastapi.testclient import TestClient

from limitx.api.main import app


def test_api_smoke_and_order_workflow():
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        snapshot = client.get("/api/book/BTC-USD").json()
        assert snapshot["type"] == "book_snapshot"
        response = client.post(
            "/api/orders",
            json={
                "order_id": "api-order-1",
                "symbol": "BTC-USD",
                "account_id": "api-user",
                "side": "BUY",
                "order_type": "LIMIT",
                "time_in_force": "GTC",
                "price_ticks": 6_784_100,
                "quantity": 3,
            },
        )
        assert response.status_code == 200
        assert response.json()["events"][0]["type"] == "ORDER_ACCEPTED"
        cancelled = client.delete(
            "/api/orders/api-order-1",
            params={"symbol": "BTC-USD", "account_id": "api-user"},
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["events"][0]["type"] == "ORDER_CANCELLED"


def test_api_validates_market_semantics():
    with TestClient(app) as client:
        response = client.post(
            "/api/orders",
            json={
                "order_id": "bad-market",
                "symbol": "BTC-USD",
                "side": "BUY",
                "order_type": "MARKET",
                "time_in_force": "GTC",
                "quantity": 3,
            },
        )
        assert response.status_code == 422


def test_observability_and_recovery_endpoints():
    with TestClient(app) as client:
        markets = client.get("/api/markets").json()["markets"]
        assert len(markets) == 4
        assert {market["symbol"] for market in markets} == {"BTC-USD", "ETH-USD", "AAPL", "MSFT"}
        xray = client.get("/api/xray/BTC-USD", params={"side": "BUY"}).json()
        assert xray["selected_level"]["head_order_id"]
        lifecycle = client.get("/api/orders/BTC-USD/SEED-BTC-USD-BUY-1/lifecycle").json()
        assert lifecycle["timeline"][0]["evidence_id"].startswith("event:")

        created = client.post("/api/recovery/snapshot/BTC-USD").json()
        assert created["snapshot_sequence"] > 0
        client.post(
            "/api/orders",
            json={
                "order_id": "after-snapshot",
                "symbol": "BTC-USD",
                "account_id": "recovery-user",
                "side": "BUY",
                "order_type": "LIMIT",
                "time_in_force": "GTC",
                "price_ticks": 6_784_100,
                "quantity": 2,
            },
        )
        recovered = client.post("/api/recovery/verify/BTC-USD").json()
        assert recovered["status"] == "PASS"
        assert recovered["commands_replayed"] >= 1


def test_experiment_and_custom_benchmark_smoke():
    with TestClient(app) as client:
        comparison = client.post(
            "/api/experiments/compare",
            json={
                "left": "normal",
                "right": "thin_liquidity",
                "symbol": "BTC-USD",
                "seed": 7,
                "operations": 100,
            },
        )
        assert comparison.status_code == 200
        assert comparison.json()["left"]["checksum"] != comparison.json()["right"]["checksum"]
        benchmark = client.post(
            "/api/benchmarks",
            json={
                "scenario": "mixed",
                "operations": 200,
                "seed": 7,
                "runs": 1,
                "symbol_count": 2,
                "add_percent": 60,
                "cancel_percent": 25,
                "modify_percent": 15,
            },
        )
        assert benchmark.status_code == 200
        assert benchmark.json()["symbol_count"] == 2
        assert benchmark.json()["latency_histogram"]
