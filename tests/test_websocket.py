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