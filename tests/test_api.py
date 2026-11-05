from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_submit_limit_order():
    response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 2,
            "price": 90,
            "trader_id": "api-buyer-1",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["order"]["symbol"] == "BTC-USD"
    assert data["order"]["side"] == "BUY"
    assert data["order"]["order_type"] == "LIMIT"
    assert data["order"]["quantity"] == 2
    assert data["order"]["price"] == 90


def test_submit_market_order():
    response = client.post(
        "/orders",
        json={
            "symbol": "ETH-USD",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": 1,
            "trader_id": "api-market-buyer-1",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["order"]["symbol"] == "ETH-USD"
    assert data["order"]["order_type"] == "MARKET"
    assert data["order"]["price"] is None


def test_get_order():
    response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 1,
            "price": 80,
            "trader_id": "api-get-order-1",
        },
    )

    assert response.status_code == 200

    order_id = response.json()["order"]["order_id"]

    response = client.get(f"/orders/{order_id}")

    assert response.status_code == 200
    assert response.json()["order_id"] == order_id


def test_get_unknown_order():
    response = client.get("/orders/does-not-exist")

    assert response.status_code == 404


def test_cancel_order():
    response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 3,
            "price": 70,
            "trader_id": "api-cancel-1",
        },
    )

    assert response.status_code == 200

    order_id = response.json()["order"]["order_id"]

    response = client.delete(f"/orders/{order_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["order_id"] == order_id
    assert data["status"] == "CANCELLED"


def test_cancelled_order_is_removed_from_order_book():
    response = client.post(
        "/orders",
        json={
            "symbol": "ETH-USD",
            "side": "SELL",
            "order_type": "LIMIT",
            "quantity": 2,
            "price": 2500,
            "trader_id": "api-book-cancel-1",
        },
    )

    assert response.status_code == 200

    order_id = response.json()["order"]["order_id"]

    response = client.delete(f"/orders/{order_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"

    response = client.get("/orderbook/ETH-USD")

    assert response.status_code == 200

    asks = response.json()["asks"]

    matching_levels = [
        level
        for level in asks
        if level["price"] == 2500
    ]

    assert matching_levels == []


def test_cannot_cancel_filled_order():
    sell_response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "SELL",
            "order_type": "LIMIT",
            "quantity": 1,
            "price": 95,
            "trader_id": "api-fill-seller-1",
        },
    )

    assert sell_response.status_code == 200

    sell_order_id = sell_response.json()["order"]["order_id"]

    buy_response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 1,
            "price": 95,
            "trader_id": "api-fill-buyer-1",
        },
    )

    assert buy_response.status_code == 200
    assert buy_response.json()["order"]["status"] == "FILLED"

    response = client.delete(
        f"/orders/{sell_order_id}"
    )

    assert response.status_code == 400


def test_cannot_cancel_order_twice():
    response = client.post(
        "/orders",
        json={
            "symbol": "ETH-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 2,
            "price": 1800,
            "trader_id": "api-double-cancel-1",
        },
    )

    assert response.status_code == 200

    order_id = response.json()["order"]["order_id"]

    first_cancel = client.delete(
        f"/orders/{order_id}"
    )

    assert first_cancel.status_code == 200
    assert first_cancel.json()["status"] == "CANCELLED"

    second_cancel = client.delete(
        f"/orders/{order_id}"
    )

    assert second_cancel.status_code == 400


def test_unknown_symbol_order_is_rejected():
    response = client.post(
        "/orders",
        json={
            "symbol": "DOGE-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 1,
            "price": 1,
            "trader_id": "api-invalid-symbol-1",
        },
    )

    assert response.status_code == 400


def test_limit_order_requires_price():
    response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 1,
            "trader_id": "api-invalid-limit-1",
        },
    )

    assert response.status_code == 400


def test_market_order_cannot_have_price():
    response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": 1,
            "price": 100,
            "trader_id": "api-invalid-market-1",
        },
    )

    assert response.status_code == 400


def test_get_btc_order_book():
    response = client.get("/orderbook/BTC-USD")

    assert response.status_code == 200

    data = response.json()

    assert data["symbol"] == "BTC-USD"
    assert "bids" in data
    assert "asks" in data


def test_get_eth_order_book():
    response = client.get("/orderbook/ETH-USD")

    assert response.status_code == 200

    data = response.json()

    assert data["symbol"] == "ETH-USD"
    assert "bids" in data
    assert "asks" in data


def test_unknown_order_book_symbol():
    response = client.get("/orderbook/DOGE-USD")

    assert response.status_code == 404


def test_get_btc_trades():
    response = client.get("/trades/BTC-USD")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_eth_trades():
    response = client.get("/trades/ETH-USD")

    assert response.status_code == 200
    assert isinstance(response.json(), list)