import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from api.main import app, reset_exchange_state


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    reset_exchange_state()
    yield
    reset_exchange_state()


def test_btc_websocket_connection():
    with client.websocket_connect("/ws/BTC-USD") as websocket:
        message = websocket.receive_json()

        assert message["event_type"] == "ORDERBOOK_SNAPSHOT"
        assert message["data"]["symbol"] == "BTC-USD"
        assert "bids" in message["data"]
        assert "asks" in message["data"]


def test_eth_websocket_connection():
    with client.websocket_connect("/ws/ETH-USD") as websocket:
        message = websocket.receive_json()

        assert message["event_type"] == "ORDERBOOK_SNAPSHOT"
        assert message["data"]["symbol"] == "ETH-USD"
        assert "bids" in message["data"]
        assert "asks" in message["data"]


def test_unknown_symbol_websocket_is_rejected():
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/DOGE-USD"):
            pass

    assert exc_info.value.code == 1008


def test_websocket_receives_trade_event():
    with client.websocket_connect("/ws/BTC-USD") as websocket:
        snapshot = websocket.receive_json()

        assert snapshot["event_type"] == "ORDERBOOK_SNAPSHOT"

        sell_response = client.post(
            "/orders",
            json={
                "symbol": "BTC-USD",
                "side": "SELL",
                "order_type": "LIMIT",
                "quantity": 2,
                "price": 100,
                "trader_id": "ws-seller-1",
            },
        )

        assert sell_response.status_code == 200

        buy_response = client.post(
            "/orders",
            json={
                "symbol": "BTC-USD",
                "side": "BUY",
                "order_type": "LIMIT",
                "quantity": 2,
                "price": 100,
                "trader_id": "ws-buyer-1",
            },
        )

        assert buy_response.status_code == 200

        received_events = []

        for _ in range(6):
            event = websocket.receive_json()
            received_events.append(event)

            if event["event_type"] == "TRADE_EXECUTED":
                break

        trade_event = next(
            event
            for event in received_events
            if event["event_type"] == "TRADE_EXECUTED"
        )

        assert trade_event["data"]["symbol"] == "BTC-USD"
        assert trade_event["data"]["price"] == 100
        assert trade_event["data"]["quantity"] == 2


def test_websocket_receives_order_submitted_event():
    with client.websocket_connect("/ws/BTC-USD") as websocket:
        snapshot = websocket.receive_json()

        assert snapshot["event_type"] == "ORDERBOOK_SNAPSHOT"

        response = client.post(
            "/orders",
            json={
                "symbol": "BTC-USD",
                "side": "SELL",
                "order_type": "LIMIT",
                "quantity": 3,
                "price": 101,
                "trader_id": "ws-submit-test",
            },
        )

        assert response.status_code == 200

        event = websocket.receive_json()

        assert event["event_type"] == "ORDER_SUBMITTED"
        assert event["data"]["symbol"] == "BTC-USD"
        assert event["data"]["side"] == "SELL"
        assert event["data"]["quantity"] == 3


def test_websocket_receives_partial_fill_event():
    with client.websocket_connect("/ws/BTC-USD") as websocket:
        snapshot = websocket.receive_json()

        assert snapshot["event_type"] == "ORDERBOOK_SNAPSHOT"

        sell_response = client.post(
            "/orders",
            json={
                "symbol": "BTC-USD",
                "side": "SELL",
                "order_type": "LIMIT",
                "quantity": 5,
                "price": 10000,
                "trader_id": "partial-seller",
            },
        )

        assert sell_response.status_code == 200

        seller_order_id = (
            sell_response.json()["order"]["order_id"]
        )

        submitted_event = websocket.receive_json()

        assert submitted_event["event_type"] == "ORDER_SUBMITTED"
        assert submitted_event["data"]["order_id"] == seller_order_id

        buy_response = client.post(
            "/orders",
            json={
                "symbol": "BTC-USD",
                "side": "BUY",
                "order_type": "LIMIT",
                "quantity": 2,
                "price": 10000,
                "trader_id": "partial-buyer",
            },
        )

        assert buy_response.status_code == 200

        events = []

        for _ in range(6):
            event = websocket.receive_json()
            events.append(event)

            if (
                event["event_type"] == "ORDER_PARTIALLY_FILLED"
                and event["data"]["order_id"] == seller_order_id
            ):
                break

        partial_event = next(
            event
            for event in events
            if (
                event["event_type"] == "ORDER_PARTIALLY_FILLED"
                and event["data"]["order_id"] == seller_order_id
            )
        )

        assert partial_event["data"]["symbol"] == "BTC-USD"
        assert partial_event["data"]["order_id"] == seller_order_id
        assert partial_event["data"]["filled_quantity"] == 2
        assert partial_event["data"]["remaining_quantity"] == 3


def test_websocket_receives_order_filled_event():
    with client.websocket_connect("/ws/ETH-USD") as websocket:
        snapshot = websocket.receive_json()

        assert snapshot["event_type"] == "ORDERBOOK_SNAPSHOT"

        sell_response = client.post(
            "/orders",
            json={
                "symbol": "ETH-USD",
                "side": "SELL",
                "order_type": "LIMIT",
                "quantity": 1,
                "price": 20000,
                "trader_id": "filled-seller",
            },
        )

        assert sell_response.status_code == 200

        buy_response = client.post(
            "/orders",
            json={
                "symbol": "ETH-USD",
                "side": "BUY",
                "order_type": "LIMIT",
                "quantity": 1,
                "price": 20000,
                "trader_id": "filled-buyer",
            },
        )

        assert buy_response.status_code == 200

        events = []

        for _ in range(8):
            event = websocket.receive_json()
            events.append(event)

            if (
                event["event_type"] == "ORDER_FILLED"
                and event["data"]["status"] == "FILLED"
            ):
                break

        filled_events = [
            event
            for event in events
            if event["event_type"] == "ORDER_FILLED"
        ]

        assert len(filled_events) >= 1

        assert any(
            event["data"]["symbol"] == "ETH-USD"
            and event["data"]["status"] == "FILLED"
            for event in filled_events
        )


def test_websocket_receives_order_cancelled_event():
    with client.websocket_connect("/ws/BTC-USD") as websocket:
        snapshot = websocket.receive_json()

        assert snapshot["event_type"] == "ORDERBOOK_SNAPSHOT"

        response = client.post(
            "/orders",
            json={
                "symbol": "BTC-USD",
                "side": "SELL",
                "order_type": "LIMIT",
                "quantity": 4,
                "price": 30000,
                "trader_id": "cancel-test",
            },
        )

        assert response.status_code == 200

        order_id = response.json()["order"]["order_id"]

        submitted_event = websocket.receive_json()

        assert submitted_event["event_type"] == "ORDER_SUBMITTED"
        assert submitted_event["data"]["order_id"] == order_id

        cancel_response = client.delete(
            f"/orders/{order_id}"
        )

        assert cancel_response.status_code == 200

        cancelled_event = websocket.receive_json()

        assert cancelled_event["event_type"] == "ORDER_CANCELLED"
        assert cancelled_event["data"]["order_id"] == order_id
        assert cancelled_event["data"]["status"] == "CANCELLED"


def test_websocket_events_are_symbol_specific():
    with (
        client.websocket_connect("/ws/BTC-USD") as btc_websocket,
        client.websocket_connect("/ws/ETH-USD") as eth_websocket,
    ):
        btc_snapshot = btc_websocket.receive_json()
        eth_snapshot = eth_websocket.receive_json()

        assert btc_snapshot["data"]["symbol"] == "BTC-USD"
        assert eth_snapshot["data"]["symbol"] == "ETH-USD"

        eth_response = client.post(
            "/orders",
            json={
                "symbol": "ETH-USD",
                "side": "SELL",
                "order_type": "LIMIT",
                "quantity": 1,
                "price": 40000,
                "trader_id": "eth-symbol-test",
            },
        )

        assert eth_response.status_code == 200

        eth_event = eth_websocket.receive_json()

        assert eth_event["event_type"] == "ORDER_SUBMITTED"
        assert eth_event["data"]["symbol"] == "ETH-USD"

        btc_response = client.post(
            "/orders",
            json={
                "symbol": "BTC-USD",
                "side": "SELL",
                "order_type": "LIMIT",
                "quantity": 1,
                "price": 40000,
                "trader_id": "btc-symbol-test",
            },
        )

        assert btc_response.status_code == 200

        btc_event = btc_websocket.receive_json()

        assert btc_event["event_type"] == "ORDER_SUBMITTED"
        assert btc_event["data"]["symbol"] == "BTC-USD"