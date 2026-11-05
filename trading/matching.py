from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable
from uuid import uuid4

from .order import Order, OrderSide
from .order_book import OrderBook


class EventType(str, Enum):
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    TRADE_EXECUTED = "TRADE_EXECUTED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_PARTIALLY_FILLED = "ORDER_PARTIALLY_FILLED"
    ORDER_CANCELLED = "ORDER_CANCELLED"


@dataclass
class Trade:
    symbol: str
    price: float
    quantity: float
    maker_order_id: str
    taker_order_id: str
    trade_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

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


@dataclass
class Event:
    event_type: EventType
    data: dict
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


class MatchingEngine:
    def __init__(self, order_book: OrderBook):
        self.order_book = order_book
        self.trades: list[Trade] = []
        self.events: list[Event] = []
        self._subscribers: list[Callable[[Event], None]] = []

    def subscribe(self, callback: Callable[[Event], None]) -> None:
        self._subscribers.append(callback)

    def publish_event(
        self,
        event_type: EventType,
        data: dict,
    ) -> Event:
        event = Event(
            event_type=event_type,
            data=data,
        )

        self.events.append(event)

        for subscriber in self._subscribers:
            subscriber(event)

        return event

    def submit_order(self, order: Order) -> list[Trade]:
        if order.symbol != self.order_book.symbol:
            raise ValueError(
                f"Order symbol {order.symbol} does not match "
                f"order book symbol {self.order_book.symbol}"
            )

        self.publish_event(
            EventType.ORDER_SUBMITTED,
            order.to_dict(),
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

            if opposite.trader_id == order.trader_id:
                raise ValueError(
                    "Self-trade prevention: "
                    "orders from the same trader cannot match"
                )

            if not self._prices_cross(order, opposite):
                break

            trade = self._execute_trade(
                order,
                opposite,
            )

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

            if opposite.trader_id == order.trader_id:
                raise ValueError(
                    "Self-trade prevention: "
                    "orders from the same trader cannot match"
                )

            trade = self._execute_trade(
                order,
                opposite,
            )

            trades.append(trade)

            if not opposite.is_active():
                self.order_book.remove_order(opposite)

        return trades

    def _get_opposite_order(
        self,
        order: Order,
    ) -> Order | None:
        if order.side == OrderSide.BUY:
            return self.order_book.get_best_order(
                OrderSide.SELL
            )

        return self.order_book.get_best_order(
            OrderSide.BUY
        )

    def _prices_cross(
        self,
        incoming: Order,
        resting: Order,
    ) -> bool:
        if (
            incoming.price is None
            or resting.price is None
        ):
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

        self.trades.append(trade)

        self.publish_event(
            EventType.TRADE_EXECUTED,
            trade.to_dict(),
        )

        if maker.status.value == "FILLED":
            self.publish_event(
                EventType.ORDER_FILLED,
                maker.to_dict(),
            )
        else:
            self.publish_event(
                EventType.ORDER_PARTIALLY_FILLED,
                maker.to_dict(),
            )

        if taker.status.value == "FILLED":
            self.publish_event(
                EventType.ORDER_FILLED,
                taker.to_dict(),
            )
        else:
            self.publish_event(
                EventType.ORDER_PARTIALLY_FILLED,
                taker.to_dict(),
            )

        return trade