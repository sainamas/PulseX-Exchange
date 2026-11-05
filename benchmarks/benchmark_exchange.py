import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from trading.matching import MatchingEngine
from trading.order import Order, OrderSide, OrderType
from trading.order_book import OrderBook


def run_benchmark(order_count: int = 10_000):
    order_book = OrderBook("BTC-USD")
    engine = MatchingEngine(order_book)

    for index in range(order_count):
        order = Order(
            symbol="BTC-USD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=1,
            price=100 + (index % 10),
            trader_id=f"seller-{index}",
        )

        order_book.add_order(order)

    start = time.perf_counter()

    matched_order = Order(
        symbol="BTC-USD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=order_count,
        trader_id="benchmark-buyer",
    )

    trades = engine.submit_order(
        matched_order
    )

    elapsed = time.perf_counter() - start

    orders_per_second = (
        order_count / elapsed
        if elapsed > 0
        else 0
    )

    total_quantity = sum(
        trade.quantity
        for trade in trades
    )

    print()
    print("=" * 50)
    print("PulseX Exchange Benchmark")
    print("=" * 50)
    print(f"Orders processed : {order_count:,}")
    print(f"Trades generated : {len(trades):,}")
    print(f"Quantity matched : {total_quantity:,.2f}")
    print(f"Elapsed time     : {elapsed:.6f} seconds")
    print(
        f"Throughput       : {orders_per_second:,.0f} orders/sec"
    )
    print("=" * 50)


if __name__ == "__main__":
    run_benchmark()