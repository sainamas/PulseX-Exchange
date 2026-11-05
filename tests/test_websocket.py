import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from api.main import app


client = TestClient(app)


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