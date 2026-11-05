from trading.matching import EventType, MatchingEngine
from trading.order import Order, OrderSide, OrderType
from trading.order_book import OrderBook


def make_order(side, order_type, quantity, price=None):
    return Order(
        symbol="BTC-USD",
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
    )


def test_trade_history_is_recorded():
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

    engine.submit_order(buy)

    assert len(engine.trades) == 1
    assert engine.trades[0].price == 100
    assert engine.trades[0].quantity == 5


def test_trade_to_dict():
    book = OrderBook("BTC-USD")
    engine = MatchingEngine(book)

    sell = make_order(
        OrderSide.SELL,
        OrderType.LIMIT,
        2,
        100,
    )

    book.add_order(sell)

    buy = make_order(
        OrderSide.BUY,
        OrderType.LIMIT,
        2,
        100,
    )

    trades = engine.submit_order(buy)
    data = trades[0].to_dict()

    assert data["symbol"] == "BTC-USD"
    assert data["price"] == 100
    assert data["quantity"] == 2
    assert "trade_id" in data
    assert "timestamp" in data


def test_events_are_recorded():
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

    engine.submit_order(buy)

    event_types = [
        event.event_type
        for event in engine.events
    ]

    assert EventType.ORDER_SUBMITTED in event_types
    assert EventType.TRADE_EXECUTED in event_types
    assert EventType.ORDER_FILLED in event_types


def test_subscriber_receives_events():
    book = OrderBook("BTC-USD")
    engine = MatchingEngine(book)

    received_events = []

    def subscriber(event):
        received_events.append(event)

    engine.subscribe(subscriber)

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

    engine.submit_order(buy)

    assert len(received_events) >= 3
    assert received_events[0].event_type == EventType.ORDER_SUBMITTED