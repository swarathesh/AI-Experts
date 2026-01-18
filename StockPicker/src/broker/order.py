"""
Order Models
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderStatus(Enum):
    NEW = "new"
    PENDING = "pending_new"
    ACCEPTED = "accepted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TimeInForce(Enum):
    DAY = "day"           # Valid for the day only
    GTC = "gtc"           # Good till cancelled
    IOC = "ioc"           # Immediate or cancel
    FOK = "fok"           # Fill or kill
    OPG = "opg"           # Market on open
    CLS = "cls"           # Market on close


@dataclass
class Order:
    """Represents a trading order"""
    symbol: str
    side: OrderSide
    qty: int
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    
    # Filled by broker
    order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.NEW
    filled_qty: int = 0
    filled_avg_price: Optional[float] = None
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "qty": self.qty,
            "type": self.order_type.value,
            "limit_price": self.limit_price,
            "stop_price": self.stop_price,
            "time_in_force": self.time_in_force.value,
            "order_id": self.order_id,
            "status": self.status.value,
            "filled_qty": self.filled_qty,
            "filled_avg_price": self.filled_avg_price
        }
