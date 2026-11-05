# This file will contain the order matching logic.
# It will match compatible buy and sell orders.
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from .order import Order, OrderSide
from .order_book import OrderBook


@dataclass
class Trade:
    symbol: str
    price: float
    quantity: float
    maker_order_id: str
    taker_order_id: str
    trade_id: str = uuid4().__str__()
    timestamp: datetime = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "price": self.price,
            "quantity": self.quantity,
            "maker_order_id": self.maker_order_id,
            "taker_order_id": self.taker_order_id,
            "timestamp": self.timestamp.isoformat(),
        }


class MatchingEngine:
    def __init__(self, order_book: OrderBook):
        self.order_book = order_book

    def submit_order(self, order: Order) -> list[Trade]:
        if order.symbol != self.order_book.symbol:
            raise ValueError(
                f"Order symbol {order.symbol} does not match "
                f"order book symbol {self.order_book.symbol}"
            )

        if order.order_type.value == "LIMIT":
            return self._match_limit_order(order)

        return self._match_market_order(order)

    def _match_limit_order(self, order: Order) -> list[Trade]:
        trades = []

        while order.is_active():
            opposite = self._get_opposite_order(order)

            if opposite is None:
                break

            if not self._prices_cross(order, opposite):
                break

            trade = self._execute_trade(order, opposite)
            trades.append(trade)

            if not opposite.is_active():
                self.order_book.remove_order(opposite)

        if order.is_active():
            self.order_book.add_order(order)

        return trades

    def _match_market_order(self, order: Order) -> list[Trade]:
        trades = []

        while order.is_active():
            opposite = self._get_opposite_order(order)

            if opposite is None:
                break

            trade = self._execute_trade(order, opposite)
            trades.append(trade)

            if not opposite.is_active():
                self.order_book.remove_order(opposite)

        return trades

    def _get_opposite_order(self, order: Order) -> Order | None:
        if order.side == OrderSide.BUY:
            return self.order_book.get_best_order(OrderSide.SELL)

        return self.order_book.get_best_order(OrderSide.BUY)

    def _prices_cross(self, incoming: Order, resting: Order) -> bool:
        if incoming.price is None or resting.price is None:
            return True

        if incoming.side == OrderSide.BUY:
            return incoming.price >= resting.price

        return incoming.price <= resting.price

    def _execute_trade(
        self,
        taker: Order,
        maker: Order,
    ) -> Trade:
        quantity = min(
            taker.remaining_quantity,
            maker.remaining_quantity,
        )

        trade = Trade(
            symbol=taker.symbol,
            price=maker.price,
            quantity=quantity,
            maker_order_id=maker.order_id,
            taker_order_id=taker.order_id,
        )

        taker.fill(quantity)
        maker.fill(quantity)

        return trade