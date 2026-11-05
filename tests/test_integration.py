from fastapi.testclient import TestClient

from api.main import app, reset_exchange_state


def setup_function():
    reset_exchange_state()


def test_limit_orders_match_through_api():
    client = TestClient(app)

    sell_response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "SELL",
            "order_type": "LIMIT",
            "quantity": 2,
            "price": 100,
            "trader_id": "seller-1",
        },
    )

    assert sell_response.status_code == 200

    buy_response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 1,
            "price": 100,
            "trader_id": "buyer-1",
        },
    )

    assert buy_response.status_code == 200

    data = buy_response.json()

    assert len(data["trades"]) == 1
    assert data["trades"][0]["price"] == 100
    assert data["trades"][0]["quantity"] == 1

    assert data["order"]["status"] == "FILLED"


def test_partial_fill_updates_orderbook():
    client = TestClient(app)

    sell_response = client.post(
        "/orders",
        json={
            "symbol": "ETH-USD",
            "side": "SELL",
            "order_type": "LIMIT",
            "quantity": 5,
            "price": 2000,
            "trader_id": "seller-1",
        },
    )

    assert sell_response.status_code == 200

    buy_response = client.post(
        "/orders",
        json={
            "symbol": "ETH-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 2,
            "price": 2000,
            "trader_id": "buyer-1",
        },
    )

    assert buy_response.status_code == 200

    sell_order_id = sell_response.json()["order"]["order_id"]

    sell_order = client.get(
        f"/orders/{sell_order_id}"
    ).json()

    assert sell_order["status"] == "PARTIALLY_FILLED"
    assert sell_order["filled_quantity"] == 2
    assert sell_order["remaining_quantity"] == 3

    book = client.get(
        "/orderbook/ETH-USD"
    ).json()

    assert len(book["asks"]) == 1
    assert book["asks"][0]["price"] == 2000
    assert book["asks"][0]["quantity"] == 3


def test_market_order_matches_multiple_levels():
    client = TestClient(app)

    orders = [
        {
            "symbol": "BTC-USD",
            "side": "SELL",
            "order_type": "LIMIT",
            "quantity": 2,
            "price": 101,
            "trader_id": "seller-101",
        },
        {
            "symbol": "BTC-USD",
            "side": "SELL",
            "order_type": "LIMIT",
            "quantity": 3,
            "price": 102,
            "trader_id": "seller-102",
        },
    ]

    for order in orders:
        response = client.post(
            "/orders",
            json=order,
        )

        assert response.status_code == 200

    response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": 5,
            "trader_id": "buyer-market",
        },
    )

    assert response.status_code == 200

    trades = response.json()["trades"]

    assert len(trades) == 2

    assert trades[0]["price"] == 101
    assert trades[0]["quantity"] == 2

    assert trades[1]["price"] == 102
    assert trades[1]["quantity"] == 3


def test_cancel_order_removes_it_from_orderbook():
    client = TestClient(app)

    response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 2,
            "price": 99,
            "trader_id": "buyer-1",
        },
    )

    assert response.status_code == 200

    order_id = response.json()["order"]["order_id"]

    book_before = client.get(
        "/orderbook/BTC-USD"
    ).json()

    assert len(book_before["bids"]) == 1
    assert book_before["bids"][0]["price"] == 99

    cancel_response = client.delete(
        f"/orders/{order_id}"
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "CANCELLED"

    book_after = client.get(
        "/orderbook/BTC-USD"
    ).json()

    assert book_after["bids"] == []


def test_market_data_endpoint():
    client = TestClient(app)

    response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 1,
            "price": 100,
            "trader_id": "buyer-1",
        },
    )

    assert response.status_code == 200

    market_data = client.get(
        "/market-data/BTC-USD"
    )

    assert market_data.status_code == 200

    data = market_data.json()

    assert data["symbol"] == "BTC-USD"
    assert data["best_bid"] == 100
    assert data["best_ask"] is None
    assert data["spread"] is None
    assert len(data["order_book"]["bids"]) == 1


def test_multiple_symbols_are_isolated():
    client = TestClient(app)

    btc_response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 1,
            "price": 100,
            "trader_id": "btc-buyer",
        },
    )

    eth_response = client.post(
        "/orders",
        json={
            "symbol": "ETH-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 2,
            "price": 2000,
            "trader_id": "eth-buyer",
        },
    )

    assert btc_response.status_code == 200
    assert eth_response.status_code == 200

    btc_book = client.get(
        "/orderbook/BTC-USD"
    ).json()

    eth_book = client.get(
        "/orderbook/ETH-USD"
    ).json()

    assert btc_book["bids"][0]["price"] == 100
    assert eth_book["bids"][0]["price"] == 2000

    assert btc_book["asks"] == []
    assert eth_book["asks"] == []


def test_self_trade_is_rejected_through_api():
    client = TestClient(app)

    sell_response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "SELL",
            "order_type": "LIMIT",
            "quantity": 1,
            "price": 100,
            "trader_id": "same-trader",
        },
    )

    assert sell_response.status_code == 200

    buy_response = client.post(
        "/orders",
        json={
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 1,
            "price": 100,
            "trader_id": "same-trader",
        },
    )

    assert buy_response.status_code == 400
    assert "Self-trade prevention" in (
        buy_response.json()["detail"]
    )


def test_order_history_filters_work():
    client = TestClient(app)

    orders = [
        {
            "symbol": "BTC-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 1,
            "price": 100,
            "trader_id": "trader-a",
        },
        {
            "symbol": "BTC-USD",
            "side": "SELL",
            "order_type": "LIMIT",
            "quantity": 2,
            "price": 101,
            "trader_id": "trader-b",
        },
        {
            "symbol": "ETH-USD",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 3,
            "price": 2000,
            "trader_id": "trader-a",
        },
    ]

    for order in orders:
        response = client.post(
            "/orders",
            json=order,
        )

        assert response.status_code == 200

    btc_orders = client.get(
        "/orders?symbol=BTC-USD"
    ).json()

    assert len(btc_orders) == 2

    trader_a_orders = client.get(
        "/orders?trader_id=trader-a"
    ).json()

    assert len(trader_a_orders) == 2

    eth_orders = client.get(
        "/orders?symbol=ETH-USD&trader_id=trader-a"
    ).json()

    assert len(eth_orders) == 1
    assert eth_orders[0]["symbol"] == "ETH-USD"