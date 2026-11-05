from trading.matching import MatchingEngine
from trading.order import Order, OrderSide, OrderStatus, OrderType
from trading.order_book import OrderBook


def make_order(
    side,
    order_type,
    quantity,
    price=None,
):
    return Order(
        symbol="BTC-USD",
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
    )


def test_limit_order_matches():
    book = OrderBook("BTC-USD")
    engine = MatchingEngine(book)

    sell = make_order(
        OrderSide.SELL,
        OrderType.LIMIT,
        5,
        100,
    )
    book.add_order(sell)

    buy = make_order(
        OrderSide.BUY,
        OrderType.LIMIT,
        5,
        100,
    )

    trades = engine.submit_order(buy)

    assert len(trades) == 1
    assert trades[0].price == 100
    assert trades[0].quantity == 5
    assert buy.status == OrderStatus.FILLED
    assert sell.status == OrderStatus.FILLED


def test_partial_fill():
    book = OrderBook("BTC-USD")
    engine = MatchingEngine(book)

    sell = make_order(
        OrderSide.SELL,
        OrderType.LIMIT,
        10,
        100,
    )
    book.add_order(sell)

    buy = make_order(
        OrderSide.BUY,
        OrderType.LIMIT,
        4,
        100,
    )

    trades = engine.submit_order(buy)

    assert len(trades) == 1
    assert trades[0].quantity == 4
    assert buy.status == OrderStatus.FILLED
    assert sell.status == OrderStatus.PARTIALLY_FILLED
    assert sell.remaining_quantity == 6


def test_remaining_limit_order_is_added_to_book():
    book = OrderBook("BTC-USD")
    engine = MatchingEngine(book)

    buy = make_order(
        OrderSide.BUY,
        OrderType.LIMIT,
        5,
        100,
    )

    trades = engine.submit_order(buy)

    assert trades == []
    assert book.get_best_order(OrderSide.BUY) is buy


def test_price_priority():
    book = OrderBook("BTC-USD")
    engine = MatchingEngine(book)

    first = make_order(
        OrderSide.SELL,
        OrderType.LIMIT,
        5,
        105,
    )
    second = make_order(
        OrderSide.SELL,
        OrderType.LIMIT,
        5,
        100,
    )

    book.add_order(first)
    book.add_order(second)

    buy = make_order(
        OrderSide.BUY,
        OrderType.LIMIT,
        5,
        110,
    )

    trades = engine.submit_order(buy)

    assert trades[0].price == 100
    assert trades[0].maker_order_id == second.order_id


def test_market_order_matches_best_available_price():
    book = OrderBook("BTC-USD")
    engine = MatchingEngine(book)

    sell = make_order(
        OrderSide.SELL,
        OrderType.LIMIT,
        5,
        100,
    )
    book.add_order(sell)

    buy = make_order(
        OrderSide.BUY,
        OrderType.MARKET,
        5,
    )

    trades = engine.submit_order(buy)

    assert len(trades) == 1
    assert trades[0].price == 100
    assert trades[0].quantity == 5
    assert buy.status == OrderStatus.FILLED# Tests for the order matching system.
# We will check whether buy and sell orders match correctly.m
