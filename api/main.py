import asyncio
from contextlib import asynccontextmanager
from queue import Queue, Empty

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from trading.matching import EventType, MatchingEngine
from trading.order import Order, OrderSide, OrderStatus, OrderType
from trading.order_book import OrderBook


SYMBOLS = {"BTC-USD", "ETH-USD"}

order_books: dict[str, OrderBook] = {}
engines: dict[str, MatchingEngine] = {}
orders: dict[str, Order] = {}


class OrderRequest(BaseModel):
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float = Field(gt=0)
    price: float | None = None
    trader_id: str = "anonymous"


class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, list[Queue]] = {
            symbol: []
            for symbol in SYMBOLS
        }

    async def connect(
        self,
        websocket: WebSocket,
        symbol: str,
    ) -> Queue:
        await websocket.accept()

        event_queue = Queue()

        self.connections[symbol].append(
            event_queue
        )

        return event_queue

    def disconnect(
        self,
        event_queue: Queue,
        symbol: str,
    ):
        if event_queue in self.connections[symbol]:
            self.connections[symbol].remove(
                event_queue
            )

    def publish(
        self,
        symbol: str,
        event,
    ):
        for event_queue in list(
            self.connections[symbol]
        ):
            event_queue.put(event)


manager = ConnectionManager()


def create_event_subscriber(symbol: str):
    def subscriber(event):
        manager.publish(
            symbol,
            event,
        )

    return subscriber


def reset_exchange_state():
    """
    Reset the in-memory exchange state.

    This is mainly useful for tests and local development.
    Each symbol receives a fresh order book and matching engine,
    while the WebSocket event subscriber remains attached.
    """

    order_books.clear()
    engines.clear()
    orders.clear()

    for symbol in SYMBOLS:
        order_book = OrderBook(symbol)

        engine = MatchingEngine(
            order_book
        )

        engine.subscribe(
            create_event_subscriber(symbol)
        )

        order_books[symbol] = order_book
        engines[symbol] = engine


reset_exchange_state()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="PulseX Exchange API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "symbols": sorted(SYMBOLS),
    }


@app.post("/orders")
def submit_order(
    request: OrderRequest,
):
    symbol = request.symbol.upper()

    if symbol not in SYMBOLS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported symbol: {symbol}",
        )

    try:
        order = Order(
            symbol=symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            price=request.price,
            trader_id=request.trader_id,
        )

        engine = engines[symbol]

        trades = engine.submit_order(
            order
        )

        orders[order.order_id] = order

        return {
            "order": order.to_dict(),
            "trades": [
                trade.to_dict()
                for trade in trades
            ],
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@app.get("/orders/{order_id}")
def get_order(
    order_id: str,
):
    order = orders.get(order_id)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    return order.to_dict()


@app.get("/orders")
def get_orders(
    symbol: str | None = None,
    trader_id: str | None = None,
    status: OrderStatus | None = None,
):
    results = list(
        orders.values()
    )

    if symbol is not None:
        symbol = symbol.upper()

        results = [
            order
            for order in results
            if order.symbol == symbol
        ]

    if trader_id is not None:
        results = [
            order
            for order in results
            if order.trader_id == trader_id
        ]

    if status is not None:
        results = [
            order
            for order in results
            if order.status == status
        ]

    return [
        order.to_dict()
        for order in results
    ]


@app.delete("/orders/{order_id}")
def cancel_order(
    order_id: str,
):
    order = orders.get(order_id)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    try:
        order.cancel()

        order_books[
            order.symbol
        ].remove_order(order)
        engines[
             order.symbol
        ].publish_event(
            EventType.ORDER_CANCELLED,
            order.to_dict(),
        )
        

        return order.to_dict()

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@app.get("/orderbook/{symbol}")
def get_orderbook(
    symbol: str,
):
    symbol = symbol.upper()

    if symbol not in SYMBOLS:
        raise HTTPException(
            status_code=404,
            detail="Unknown symbol",
        )

    return order_books[
        symbol
    ].depth()


@app.get("/trades/{symbol}")
def get_trades(
    symbol: str,
):
    symbol = symbol.upper()

    if symbol not in SYMBOLS:
        raise HTTPException(
            status_code=404,
            detail="Unknown symbol",
        )

    return [
        trade.to_dict()
        for trade in engines[
            symbol
        ].trades
    ]


@app.websocket("/ws/{symbol}")
async def websocket_endpoint(
    websocket: WebSocket,
    symbol: str,
):
    symbol = symbol.upper()

    if symbol not in SYMBOLS:
        await websocket.close(
            code=1008
        )
        return

    event_queue = await manager.connect(
        websocket,
        symbol,
    )

    try:
        await websocket.send_json(
            {
                "event_type": "ORDERBOOK_SNAPSHOT",
                "data": order_books[
                    symbol
                ].depth(),
            }
        )

        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=0.05,
                )

                if message:
                    continue

            except asyncio.TimeoutError:
                pass

            while True:
                try:
                    event = event_queue.get_nowait()

                except Empty:
                    break

                await websocket.send_json(
                    event.to_dict()
                )

    except WebSocketDisconnect:
        manager.disconnect(
            event_queue,
            symbol,
        )