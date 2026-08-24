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
                "price_ticks": 9_999_900,
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
