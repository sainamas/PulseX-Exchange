# This file will manage buy and sell orders.
from collections import defaultdict, deque

from .order import Order, OrderSide


class OrderBook:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.bids = defaultdict(deque)
        self.asks = defaultdict(deque)

    def add_order(self, order: Order) -> None:
        if order.symbol != self.symbol:
            raise ValueError(
                f"Order symbol {order.symbol} does not match "
                f"order book symbol {self.symbol}"
            )

        if order.price is None:
            raise ValueError("Only limit orders can be added to the order book")

        if not order.is_active():
            raise ValueError("Only active orders can be added to the order book")

        if order.side == OrderSide.BUY:
            self.bids[order.price].append(order)
        else:
            self.asks[order.price].append(order)

    def best_bid(self) -> float | None:
        if not self.bids:
            return None
        return max(self.bids)

    def best_ask(self) -> float | None:
        if not self.asks:
            return None
        return min(self.asks)

    def spread(self) -> float | None:
        bid = self.best_bid()
        ask = self.best_ask()

        if bid is None or ask is None:
            return None

        return ask - bid

    def get_best_order(self, side: OrderSide) -> Order | None:
        levels = self.bids if side == OrderSide.BUY else self.asks
        price = self.best_bid() if side == OrderSide.BUY else self.best_ask()

        if price is None:
            return None

        queue = levels[price]

        while queue and not queue[0].is_active():
            queue.popleft()

        if not queue:
            del levels[price]
            return self.get_best_order(side)

        return queue[0]

    def remove_order(self, order: Order) -> bool:
        if order.price is None:
            return False

        levels = self.bids if order.side == OrderSide.BUY else self.asks
        queue = levels.get(order.price)

        if queue is None:
            return False

        try:
            queue.remove(order)
        except ValueError:
            return False

        if not queue:
            del levels[order.price]

        return True

    def depth(self, levels: int = 5) -> dict:
        bids = sorted(
            [
                {
                    "price": price,
                    "quantity": self._level_quantity(queue),
                }
                for price, queue in self.bids.items()
            ],
            key=lambda level: level["price"],
            reverse=True,
        )[:levels]

        asks = sorted(
            [
                {
                    "price": price,
                    "quantity": self._level_quantity(queue),
                }
                for price, queue in self.asks.items()
            ],
            key=lambda level: level["price"],
        )[:levels]

        return {
            "symbol": self.symbol,
            "bids": bids,
            "asks": asks,
        }

    @staticmethod
    def _level_quantity(queue: deque) -> float:
        return sum(
            order.remaining_quantity
            for order in queue
            if order.is_active()
        )