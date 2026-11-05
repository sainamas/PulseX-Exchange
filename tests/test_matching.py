from trading.matching import MatchingEngine
from trading.order import Order, OrderSide, OrderType
from trading.order_book import OrderBook


def make_order(
    side,
    quantity,
    price=None,
    order_type=OrderType.LIMIT,
    trader_id="trader-1",
):
    return Order(
        symbol="BTC-USD",
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        trader_id=trader_id,
    )


def test_limit_order_matches():
    book = OrderBook("BTC-USD")
    engine = MatchingEngine(book)

    sell = make_order(
        OrderSide.SELL,
        5,
        100,
        trader_id="seller-1",
    )
    book.add_order(sell)

    buy = make_order(
        OrderSide.BUY,
        5,
        100,
        trader_id="buyer-1",
    )

    trades = engine.submit_order(buy)

    assert len(trades) == 1
    assert trades[0].price == 100
    assert trades[0].quantity == 5
    assert buy.status.value == "FILLED"
    assert sell.status.value == "FILLED"


def test_partial_fill():
    book = OrderBook("BTC-USD")
    engine = MatchingEngine(book)

    sell = make_order(
        OrderSide.SELL,
        10,
        100,
        trader_id="seller-1",
    )
    book.add_order(sell)

    buy = make_order(
        OrderSide.BUY,
        4,
        100,
        trader_id="buyer-1",
    )

    trades = engine.submit_order(buy)

    assert len(trades) == 1
    assert trades[0].quantity == 4
    assert buy.status.value == "FILLED"
    assert sell.status.value == "PARTIALLY_FILLED"
    assert sell.remaining_quantity == 6


def test_price_priority():
    book = OrderBook("BTC-USD")
    engine = MatchingEngine(book)

    sell_high = make_order(
        OrderSide.SELL,
        5,
        105,
        trader_id="seller-1",
    )

    sell_low = make_order(
        OrderSide.SELL,
        5,
        100,
        trader_id="seller-2",
    )

    book.add_order(sell_high)
    book.add_order(sell_low)

    buy = make_order(
        OrderSide.BUY,
        5,
        110,
        trader_id="buyer-1",
    )

    trades = engine.submit_order(buy)

    assert len(trades) == 1
    assert trades[0].price == 100
    assert trades[0].quantity == 5


def test_fifo_priority():
    book = OrderBook("BTC-USD")
    engine = MatchingEngine(book)

    first_sell = make_order(
        OrderSide.SELL,
        5,
        100,
        trader_id="seller-1",
    )

    second_sell = make_order(
        OrderSide.SELL,
        5,
        100,
        trader_id="seller-2",
    )

    book.add_order(first_sell)
    book.add_order(second_sell)

    buy = make_order(
        OrderSide.BUY,
        5,
        100,
        trader_id="buyer-1",
    )

    trades = engine.submit_order(buy)

    assert len(trades) == 1
    assert trades[0].maker_order_id == first_sell.order_id
    assert first_sell.status.value == "FILLED"
    assert second_sell.status.value == "NEW"


def test_market_order_matches_best_available_price():
    book = OrderBook("BTC-USD")
    engine = MatchingEngine(book)

    sell_low = make_order(
        OrderSide.SELL,
        5,
        100,
        trader_id="seller-1",
    )

    sell_high = make_order(
        OrderSide.SELL,
        5,
        105,
        trader_id="seller-2",
    )

    book.add_order(sell_high)
    book.add_order(sell_low)

    buy = make_order(
        OrderSide.BUY,
        5,
        order_type=OrderType.MARKET,
        trader_id="buyer-1",
    )

    trades = engine.submit_order(buy)

    assert len(trades) == 1
    assert trades[0].price == 100
    assert trades[0].quantity == 5


def test_market_order_consumes_multiple_price_levels():
    book = OrderBook("BTC-USD")
    engine = MatchingEngine(book)

    first_sell = make_order(
        OrderSide.SELL,
        3,
        100,
        trader_id="seller-1",
    )

    second_sell = make_order(
        OrderSide.SELL,
        4,
        101,
        trader_id="seller-2",
    )

    third_sell = make_order(
        OrderSide.SELL,
        5,
        102,
        trader_id="seller-3",
    )

    book.add_order(first_sell)
    book.add_order(second_sell)
    book.add_order(third_sell)

    market_buy = make_order(
        OrderSide.BUY,
        9,
        order_type=OrderType.MARKET,
        trader_id="buyer-1",
    )

    trades = engine.submit_order(market_buy)

    assert len(trades) == 3

    assert trades[0].price == 100
    assert trades[0].quantity == 3

    assert trades[1].price == 101
    assert trades[1].quantity == 4

    assert trades[2].price == 102
    assert trades[2].quantity == 2

    assert market_buy.status.value == "FILLED"

    assert first_sell.status.value == "FILLED"
    assert second_sell.status.value == "FILLED"
    assert third_sell.status.value == "PARTIALLY_FILLED"

    assert third_sell.remaining_quantity == 3


def test_market_order_consumes_available_liquidity():
    book = OrderBook("BTC-USD")
    engine = MatchingEngine(book)

    sell = make_order(
        OrderSide.SELL,
        3,
        100,
        trader_id="seller-1",
    )

    book.add_order(sell)

    market_buy = make_order(
        OrderSide.BUY,
        10,
        order_type=OrderType.MARKET,
        trader_id="buyer-1",
    )

    trades = engine.submit_order(market_buy)

    assert len(trades) == 1
    assert trades[0].price == 100
    assert trades[0].quantity == 3

    assert sell.status.value == "FILLED"
    assert market_buy.status.value == "PARTIALLY_FILLED"
    assert market_buy.remaining_quantity == 7

    assert book.best_ask() is None


def test_market_sell_consumes_multiple_bid_levels():
    book = OrderBook("BTC-USD")
    engine = MatchingEngine(book)

    first_buy = make_order(
        OrderSide.BUY,
        2,
        100,
        trader_id="buyer-1",
    )

    second_buy = make_order(
        OrderSide.BUY,
        3,
        99,
        trader_id="buyer-2",
    )

    third_buy = make_order(
        OrderSide.BUY,
        4,
        98,
        trader_id="buyer-3",
    )

    book.add_order(first_buy)
    book.add_order(second_buy)
    book.add_order(third_buy)

    market_sell = make_order(
        OrderSide.SELL,
        7,
        order_type=OrderType.MARKET,
        trader_id="seller-1",
    )

    trades = engine.submit_order(market_sell)

    assert len(trades) == 3

    assert trades[0].price == 100
    assert trades[0].quantity == 2

    assert trades[1].price == 99
    assert trades[1].quantity == 3

    assert trades[2].price == 98
    assert trades[2].quantity == 2

    assert market_sell.status.value == "FILLED"

    assert first_buy.status.value == "FILLED"
    assert second_buy.status.value == "FILLED"
    assert third_buy.status.value == "PARTIALLY_FILLED"

    assert third_buy.remaining_quantity == 2