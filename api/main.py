from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from trading.matching import EventType, MatchingEngine
from trading.order import Order, OrderSide, OrderType
from trading.order_book import OrderBook


app = FastAPI(
    title="PulseX Exchange API",
    version="1.0.0",
)

order_book = OrderBook("BTC-USD")
engine = MatchingEngine(order_book)
orders: dict[str, Order] = {}


class OrderRequest(BaseModel):
    symbol: str = "BTC-USD"
    side: OrderSide
    order_type: OrderType
    quantity: float = Field(gt=0)
    price: float | None = Field(default=None, gt=0)
    trader_id: str = "anonymous"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "PulseX Exchange",
    }


@app.post("/orders")
def submit_order(request: OrderRequest):
    if request.symbol != order_book.symbol:
        raise HTTPException(
            status_code=400,
            detail="Unsupported trading symbol",
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
        symbol=request.symbol,
        side=request.side,
        order_type=request.order_type,
        quantity=request.quantity,
        price=request.price,
        trader_id=request.trader_id,
    )

    orders[order.order_id] = order

    trades = engine.submit_order(order)

    return {
        "order": order.to_dict(),
        "trades": [
            trade.to_dict()
            for trade in trades
        ],
    }


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
    order_book.remove_order(order)

    engine._publish(
        EventType.ORDER_CANCELLED,
        order.to_dict(),
    )

    return order.to_dict()


@app.get("/orderbook")
def get_order_book():
    return order_book.depth()


@app.get("/trades")
def get_trades():
    return [
        trade.to_dict()
        for trade in engine.trades
    ]