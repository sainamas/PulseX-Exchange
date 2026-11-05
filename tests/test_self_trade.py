import pytest

from trading.matching import MatchingEngine
from trading.order import Order, OrderSide, OrderType
from trading.order_book import OrderBook


def make_order(
    side,
    quantity,
    price,
    trader_id,
):
    return Order(
        symbol="BTC-USD",
        side=side,
        order_type=OrderType.LIMIT,
        quantity=quantity,
        price=price,
        trader_id=trader_id,
    )


def test_self_trade_is_prevented():
    book = OrderBook("BTC-USD")
    engine = MatchingEngine(book)

    sell = make_order(
        OrderSide.SELL,
        5,
        100,
        "trader-1",
    )

    book.add_order(sell)

    buy = make_order(
        OrderSide.BUY,
        5,
        100,
        "trader-1",
    )

    with pytest.raises(ValueError, match="Self-trade prevention"):
        engine.submit_order(buy)

    assert len(engine.trades) == 0
    assert sell.remaining_quantity == 5


def test_different_traders_can_trade():
    book = OrderBook("BTC-USD")
    engine = MatchingEngine(book)

    sell = make_order(
        OrderSide.SELL,
        5,
        100,
        "trader-1",
    )

    book.add_order(sell)

    buy = make_order(
        OrderSide.BUY,
        5,
        100,
        "trader-2",
    )

    trades = engine.submit_order(buy)

    assert len(trades) == 1
    assert trades[0].quantity == 5