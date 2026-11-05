import pytest

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


def test_limit_order_requires_price():
    with pytest.raises(ValueError):
        Order(
            symbol="BTC-USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=5,
        )


def test_market_order_cannot_have_price():
    with pytest.raises(ValueError):
        Order(
            symbol="BTC-USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=5,
            price=100,
        )


def test_order_quantity_must_be_positive():
    with pytest.raises(ValueError):
        Order(
            symbol="BTC-USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0,
            price=100,
        )


def test_order_price_must_be_positive():
    with pytest.raises(ValueError):
        Order(
            symbol="BTC-USD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=5,
            price=0,
        )