from trading.matching import EventType, MatchingEngine
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


def setup_trade():
    book = OrderBook("BTC-USD")
    engine = MatchingEngine(book)

    sell = make_order(
        OrderSide.SELL,
        5,
        100,
        "seller-1",
    )

    book.add_order(sell)

    buy = make_order(
        OrderSide.BUY,
        5,
        100,
        "buyer-1",
    )

    return engine, sell, buy


def test_trade_history_is_recorded():
    engine, _, buy = setup_trade()

    trades = engine.submit_order(buy)

    assert len(trades) == 1
    assert len(engine.trades) == 1

    trade = engine.trades[0]

    assert trade.symbol == "BTC-USD"
    assert trade.price == 100
    assert trade.quantity == 5


def test_trade_to_dict():
    engine, _, buy = setup_trade()

    trades = engine.submit_order(buy)

    trade_data = trades[0].to_dict()

    assert trade_data["symbol"] == "BTC-USD"
    assert trade_data["price"] == 100
    assert trade_data["quantity"] == 5
    assert "trade_id" in trade_data
    assert "maker_order_id" in trade_data
    assert "taker_order_id" in trade_data
    assert "timestamp" in trade_data


def test_events_are_recorded():
    engine, _, buy = setup_trade()

    engine.submit_order(buy)

    event_types = [
        event.event_type
        for event in engine.events
    ]

    assert EventType.ORDER_SUBMITTED in event_types
    assert EventType.TRADE_EXECUTED in event_types
    assert EventType.ORDER_FILLED in event_types


def test_subscriber_receives_events():
    engine, _, buy = setup_trade()

    received_events = []

    def subscriber(event):
        received_events.append(event)

    engine.subscribe(subscriber)

    engine.submit_order(buy)

    assert len(received_events) > 0

    event_types = [
        event.event_type
        for event in received_events
    ]

    assert EventType.ORDER_SUBMITTED in event_types
    assert EventType.TRADE_EXECUTED in event_types
    assert EventType.ORDER_FILLED in event_types