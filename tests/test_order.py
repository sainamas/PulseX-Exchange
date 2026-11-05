from trading.order import (
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
)


def test_create_limit_order():
    order = Order(
        symbol="BTC-USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=5,
        price=100,
    )

    assert order.quantity == 5
    assert order.remaining_quantity == 5
    assert order.filled_quantity == 0
    assert order.status == OrderStatus.NEW


def test_partial_fill():
    order = Order(
        symbol="BTC-USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=5,
        price=100,
    )

    order.fill(2)

    assert order.filled_quantity == 2
    assert order.remaining_quantity == 3
    assert order.status == OrderStatus.PARTIALLY_FILLED


def test_full_fill():
    order = Order(
        symbol="BTC-USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=5,
        price=100,
    )

    order.fill(5)

    assert order.filled_quantity == 5
    assert order.remaining_quantity == 0
    assert order.status == OrderStatus.FILLED


def test_cancel_order():
    order = Order(
        symbol="BTC-USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=5,
        price=100,
    )

    order.cancel()

    assert order.status == OrderStatus.CANCELLED