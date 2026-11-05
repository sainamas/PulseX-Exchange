from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_order_history_returns_submitted_order():
    response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 2,
            "price": 90,
            "trader_id": "history-buyer-1",
        },
    )

    assert response.status_code == 200

    created_order = response.json()["order"]
    order_id = created_order["order_id"]

    response = client.get("/orders")

    assert response.status_code == 200

    order_ids = [
        order["order_id"]
        for order in response.json()
    ]

    assert order_id in order_ids


def test_order_history_can_filter_by_trader():
    response = client.post(
        "/orders",
        json={
            "symbol": "ETH-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 1,
            "price": 2000,
            "trader_id": "history-trader-unique",
        },
    )

    assert response.status_code == 200

    response = client.get(
        "/orders?trader_id=history-trader-unique"
    )

    assert response.status_code == 200

    orders = response.json()

    assert len(orders) >= 1

    for order in orders:
        assert order["trader_id"] == "history-trader-unique"


def test_order_history_can_filter_by_symbol():
    response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "SELL",
            "order_type": "LIMIT",
            "quantity": 1,
            "price": 50000,
            "trader_id": "btc-history-trader",
        },
    )

    assert response.status_code == 200

    response = client.get("/orders?symbol=BTC-USD")

    assert response.status_code == 200

    orders = response.json()

    assert len(orders) >= 1

    for order in orders:
        assert order["symbol"] == "BTC-USD"


def test_order_history_can_filter_by_status():
    response = client.post(
        "/orders",
        json={
            "symbol": "ETH-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 1,
            "price": 1000,
            "trader_id": "status-history-trader",
        },
    )

    assert response.status_code == 200

    response = client.get("/orders?status=NEW")

    assert response.status_code == 200

    orders = response.json()

    for order in orders:
        assert order["status"] == "NEW"