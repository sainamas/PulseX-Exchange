from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderStatus(str, Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"


@dataclass
class Order:
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float

    price: float | None = None

    order_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    trader_id: str = "anonymous"

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    filled_quantity: float = 0.0
    status: OrderStatus = OrderStatus.NEW

    @property
    def remaining_quantity(self) -> float:
        return self.quantity - self.filled_quantity

    def fill(self, quantity: float) -> None:
        if quantity <= 0:
            raise ValueError(
                "Fill quantity must be greater than zero"
            )

        if quantity > self.remaining_quantity:
            raise ValueError(
                "Fill quantity exceeds remaining quantity"
            )

        self.filled_quantity += quantity

        if self.remaining_quantity == 0:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED

    def cancel(self) -> None:
        if self.status == OrderStatus.FILLED:
            raise ValueError(
                "Filled order cannot be cancelled"
            )

        self.status = OrderStatus.CANCELLED

    def is_active(self) -> bool:
        return self.status in {
            OrderStatus.NEW,
            OrderStatus.PARTIALLY_FILLED,
        }

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "trader_id": self.trader_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "price": self.price,
            "quantity": self.quantity,
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.remaining_quantity,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
        }