from trading.order import Order, OrderSide, OrderType
from trading.order_book import OrderBook


def make_order(
    side: OrderSide,
    price: float,
    quantity: float,
) -> Order:
    return Order(
        symbol="BTC-USD",
        side=side,
        order_type=OrderType.LIMIT,
        quantity=quantity,
        price=price,
    )


def test_best_bid_and_ask():
    book = OrderBook("BTC-USD")

    book.add_order(make_order(OrderSide.BUY, 100, 5))
    book.add_order(make_order(OrderSide.BUY, 105, 3))
    book.add_order(make_order(OrderSide.SELL, 110, 2))
    book.add_order(make_order(OrderSide.SELL, 101, 4))

    assert book.best_bid() == 105
    assert book.best_ask() == 101


def test_spread():
    book = OrderBook("BTC-USD")

    book.add_order(make_order(OrderSide.BUY, 100, 5))
    book.add_order(make_order(OrderSide.SELL, 105, 5))

    assert book.spread() == 5


def test_fifo_at_same_price():
    book = OrderBook("BTC-USD")

    first = make_order(OrderSide.BUY, 100, 5)
    second = make_order(OrderSide.BUY, 100, 3)

    book.add_order(first)
    book.add_order(second)

    assert book.get_best_order(OrderSide.BUY) is first


def test_price_priority():
    book = OrderBook("BTC-USD")

    lower = make_order(OrderSide.BUY, 100, 5)
    higher = make_order(OrderSide.BUY, 105, 3)

    book.add_order(lower)
    book.add_order(higher)

    assert book.get_best_order(OrderSide.BUY) is higher


def test_remove_order():
    book = OrderBook("BTC-USD")

    order = make_order(OrderSide.BUY, 100, 5)
    book.add_order(order)

    assert book.remove_order(order)
    assert book.best_bid() is None


def test_depth():
    book = OrderBook("BTC-USD")

    book.add_order(make_order(OrderSide.BUY, 100, 5))
    book.add_order(make_order(OrderSide.BUY, 105, 3))
    book.add_order(make_order(OrderSide.SELL, 110, 2))
    book.add_order(make_order(OrderSide.SELL, 101, 4))

    depth = book.depth()

    assert depth["bids"][0] == {
        "price": 105,
        "quantity": 3,
    }

    assert depth["asks"][0] == {
        "price": 101,
        "quantity": 4,
    }