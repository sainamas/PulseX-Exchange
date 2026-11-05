from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_websocket_connection():
    with client.websocket_connect("/ws") as websocket:
        message = websocket.receive_json()

        assert message["event_type"] == "ORDERBOOK_SNAPSHOT"
        assert message["data"]["symbol"] == "BTC-USD"
        assert "bids" in message["data"]
        assert "asks" in message["data"]