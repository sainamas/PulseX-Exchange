from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_lists_symbols():
    response = client.get("/health")

    assert response.json()["symbols"] == [
        "BTC-USD",
        "ETH-USD",
    ]


def test_submit_btc_limit_order():
    response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 2,
            "price": 100,
            "trader_id": "trader-1",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["order"]["symbol"] == "BTC-USD"
    assert data["order"]["status"] == "NEW"


def test_submit_eth_limit_order():
    response = client.post(
        "/orders",
        json={
            "symbol": "ETH-USD",
            "side": "SELL",
            "order_type": "LIMIT",
            "quantity": 3,
            "price": 200,
        },
    )

    assert response.status_code == 200

    assert response.json()["order"]["symbol"] == "ETH-USD"


def test_unsupported_symbol():
    response = client.post(
        "/orders",
        json={
            "symbol": "DOGE-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 1,
            "price": 10,
        },
    )

    assert response.status_code == 400


def test_invalid_limit_order_without_price():
    response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 2,
        },
    )

    assert response.status_code == 400


def test_invalid_market_order_with_price():
    response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": 2,
            "price": 100,
        },
    )

    assert response.status_code == 400


def test_orderbook_endpoint():
    response = client.get("/orderbook/BTC-USD")

    assert response.status_code == 200

    data = response.json()

    assert data["symbol"] == "BTC-USD"
    assert "bids" in data
    assert "asks" in data


def test_eth_orderbook_endpoint():
    response = client.get("/orderbook/ETH-USD")

    assert response.status_code == 200

    assert response.json()["symbol"] == "ETH-USD"


def test_unknown_orderbook_symbol():
    response = client.get("/orderbook/DOGE-USD")

    assert response.status_code == 404


def test_get_order():
    create_response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 1,
            "price": 90,
        },
    )

    order_id = create_response.json()["order"]["order_id"]

    response = client.get(f"/orders/{order_id}")

    assert response.status_code == 200
    assert response.json()["order_id"] == order_id


def test_cancel_order():
    create_response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 1,
            "price": 80,
        },
    )

    order_id = create_response.json()["order"]["order_id"]

    response = client.delete(f"/orders/{order_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_trades_endpoint():
    response = client.get("/trades/BTC-USD")

    assert response.status_code == 200
    assert isinstance(response.json(), list)