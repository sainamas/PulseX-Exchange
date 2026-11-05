from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from trading.matching import Event, EventType, MatchingEngine
from trading.order import Order, OrderSide, OrderStatus, OrderType
from trading.order_book import OrderBook


SYMBOLS = {
    "BTC-USD",
    "ETH-USD",
}


order_books: dict[str, OrderBook] = {
    symbol: OrderBook(symbol)
    for symbol in SYMBOLS
}

engines: dict[str, MatchingEngine] = {
    symbol: MatchingEngine(order_books[symbol])
    for symbol in SYMBOLS
}

orders: dict[str, Order] = {}


class OrderRequest(BaseModel):
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float = Field(gt=0)
    price: float | None = Field(default=None, gt=0)
    trader_id: str = "anonymous"


class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def broadcast(self, event: Event):
        disconnected = []

        for websocket in self.connections:
            try:
                await websocket.send_json(event.to_dict())
            except Exception:
                disconnected.append(websocket)

        for websocket in disconnected:
            self.disconnect(websocket)


manager = ConnectionManager()


def create_event_subscriber():
    def subscriber(event: Event):
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(manager.broadcast(event))
        except RuntimeError:
            pass

    return subscriber


for engine in engines.values():
    engine.subscribe(create_event_subscriber())


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
        "service": "PulseX Exchange",
        "symbols": sorted(SYMBOLS),
    }


@app.post("/orders")
def submit_order(request: OrderRequest):
    symbol = request.symbol.upper()

    if symbol not in SYMBOLS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported trading symbol: {symbol}",
        )

    if (
        request.order_type == OrderType.LIMIT
        and request.price is None
    ):
        raise HTTPException(
            status_code=400,
            detail="Limit orders require a price",
        )

    if (
        request.order_type == OrderType.MARKET
        and request.price is not None
    ):
        raise HTTPException(
            status_code=400,
            detail="Market orders must not have a price",
        )

    order = Order(
        symbol=symbol,
        side=request.side,
        order_type=request.order_type,
        quantity=request.quantity,
        price=request.price,
        trader_id=request.trader_id,
    )

    orders[order.order_id] = order

    try:
        trades = engines[symbol].submit_order(order)
    except ValueError as exc:
        orders.pop(order.order_id, None)

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return {
        "order": order.to_dict(),
        "trades": [
            trade.to_dict()
            for trade in trades
        ],
    }


@app.get("/orders")
def list_orders(
    symbol: str | None = None,
    trader_id: str | None = None,
    status: OrderStatus | None = None,
):
    filtered_orders = list(orders.values())

    if symbol is not None:
        symbol = symbol.upper()

        if symbol not in SYMBOLS:
            raise HTTPException(
                status_code=404,
                detail="Trading symbol not found",
            )

        filtered_orders = [
            order
            for order in filtered_orders
            if order.symbol == symbol
        ]

    if trader_id is not None:
        filtered_orders = [
            order
            for order in filtered_orders
            if order.trader_id == trader_id
        ]

    if status is not None:
        filtered_orders = [
            order
            for order in filtered_orders
            if order.status == status
        ]

    return [
        order.to_dict()
        for order in filtered_orders
    ]


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    order = orders.get(order_id)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    return order.to_dict()


@app.delete("/orders/{order_id}")
def cancel_order(order_id: str):
    order = orders.get(order_id)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    if not order.is_active():
        raise HTTPException(
            status_code=400,
            detail=f"Order is {order.status.value.lower()}",
        )

    order.cancel()

    order_book = order_books[order.symbol]
    order_book.remove_order(order)

    engines[order.symbol]._publish(
        EventType.ORDER_CANCELLED,
        order.to_dict(),
    )

    return order.to_dict()


@app.get("/orderbook/{symbol}")
def get_order_book(symbol: str):
    symbol = symbol.upper()

    if symbol not in SYMBOLS:
        raise HTTPException(
            status_code=404,
            detail="Trading symbol not found",
        )

    return order_books[symbol].depth()


@app.get("/trades/{symbol}")
def get_trades(symbol: str):
    symbol = symbol.upper()

    if symbol not in SYMBOLS:
        raise HTTPException(
            status_code=404,
            detail="Trading symbol not found",
        )

    return [
        trade.to_dict()
        for trade in engines[symbol].trades
    ]


@app.websocket("/ws/{symbol}")
async def websocket_endpoint(
    websocket: WebSocket,
    symbol: str,
):
    symbol = symbol.upper()

    if symbol not in SYMBOLS:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket)

    try:
        await websocket.send_json({
            "event_type": "ORDERBOOK_SNAPSHOT",
            "data": order_books[symbol].depth(),
        })

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket)