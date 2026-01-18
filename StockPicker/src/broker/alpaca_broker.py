"""
Alpaca Broker Integration
Handles real and paper trading via Alpaca API
"""
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import (
        MarketOrderRequest,
        LimitOrderRequest,
        StopOrderRequest,
        StopLimitOrderRequest,
        TrailingStopOrderRequest,
        GetOrdersRequest
    )
    from alpaca.trading.enums import OrderSide as AlpacaOrderSide
    from alpaca.trading.enums import TimeInForce as AlpacaTIF
    from alpaca.trading.enums import OrderType as AlpacaOrderType
    from alpaca.trading.enums import QueryOrderStatus
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    logger.warning("Alpaca SDK not installed. Run: pip install alpaca-py")

from .order import Order, OrderSide, OrderType, OrderStatus, TimeInForce


class AlpacaBroker:
    """
    Alpaca Trading Broker
    
    Supports both paper trading (simulation) and live trading.
    Paper trading is recommended for testing strategies.
    
    Get your API keys at: https://app.alpaca.markets/
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        paper: bool = True  # Use paper trading by default for safety
    ):
        """
        Initialize Alpaca broker
        
        Args:
            api_key: Alpaca API key (or set ALPACA_API_KEY env var)
            secret_key: Alpaca secret key (or set ALPACA_SECRET_KEY env var)
            paper: If True, use paper trading (simulated). Default True for safety.
        """
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")
        self.paper = paper
        self.client = None
        self.connected = False
        
        if not ALPACA_AVAILABLE:
            logger.error("Alpaca SDK not available. Install with: pip install alpaca-py")
            return
        
        if self.api_key and self.secret_key:
            self._connect()
    
    def _connect(self):
        """Establish connection to Alpaca"""
        try:
            self.client = TradingClient(
                api_key=self.api_key,
                secret_key=self.secret_key,
                paper=self.paper
            )
            # Test connection by getting account
            account = self.client.get_account()
            self.connected = True
            
            mode = "PAPER" if self.paper else "LIVE"
            logger.info(f"✅ Connected to Alpaca ({mode} trading)")
            logger.info(f"   Account: {account.account_number}")
            logger.info(f"   Buying Power: ${float(account.buying_power):,.2f}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Alpaca: {e}")
            self.connected = False
    
    def get_account(self) -> Optional[Dict]:
        """Get account information"""
        if not self.connected:
            logger.error("Not connected to Alpaca")
            return None
        
        try:
            account = self.client.get_account()
            return {
                "account_number": account.account_number,
                "status": account.status,
                "currency": account.currency,
                "cash": float(account.cash),
                "buying_power": float(account.buying_power),
                "portfolio_value": float(account.portfolio_value),
                "equity": float(account.equity),
                "last_equity": float(account.last_equity),
                "long_market_value": float(account.long_market_value),
                "short_market_value": float(account.short_market_value),
                "initial_margin": float(account.initial_margin),
                "maintenance_margin": float(account.maintenance_margin),
                "daytrade_count": account.daytrade_count,
                "pattern_day_trader": account.pattern_day_trader
            }
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return None
    
    def get_positions(self) -> List[Dict]:
        """Get all current positions"""
        if not self.connected:
            return []
        
        try:
            positions = self.client.get_all_positions()
            return [
                {
                    "symbol": pos.symbol,
                    "qty": int(pos.qty),
                    "side": pos.side,
                    "avg_entry_price": float(pos.avg_entry_price),
                    "current_price": float(pos.current_price),
                    "market_value": float(pos.market_value),
                    "cost_basis": float(pos.cost_basis),
                    "unrealized_pl": float(pos.unrealized_pl),
                    "unrealized_plpc": float(pos.unrealized_plpc),
                    "change_today": float(pos.change_today)
                }
                for pos in positions
            ]
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position for a specific symbol"""
        if not self.connected:
            return None
        
        try:
            pos = self.client.get_open_position(symbol)
            return {
                "symbol": pos.symbol,
                "qty": int(pos.qty),
                "avg_entry_price": float(pos.avg_entry_price),
                "current_price": float(pos.current_price),
                "market_value": float(pos.market_value),
                "unrealized_pl": float(pos.unrealized_pl),
                "unrealized_plpc": float(pos.unrealized_plpc)
            }
        except Exception as e:
            logger.debug(f"No position for {symbol}: {e}")
            return None
    
    def buy(
        self,
        symbol: str,
        qty: Optional[int] = None,
        notional: Optional[float] = None,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: TimeInForce = TimeInForce.DAY
    ) -> Optional[Order]:
        """
        Place a buy order
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            qty: Number of shares to buy (use qty OR notional, not both)
            notional: Dollar amount to buy (e.g., $1000 of AAPL)
            order_type: Market, Limit, Stop, etc.
            limit_price: Limit price for limit orders
            stop_price: Stop price for stop orders
            time_in_force: How long order stays active
        
        Returns:
            Order object if successful, None otherwise
        """
        return self._place_order(
            symbol=symbol,
            side=OrderSide.BUY,
            qty=qty,
            notional=notional,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            time_in_force=time_in_force
        )
    
    def sell(
        self,
        symbol: str,
        qty: Optional[int] = None,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: TimeInForce = TimeInForce.DAY
    ) -> Optional[Order]:
        """
        Place a sell order
        
        Args:
            symbol: Stock symbol
            qty: Number of shares to sell (None = sell all)
            order_type: Market, Limit, Stop, etc.
            limit_price: Limit price for limit orders
            stop_price: Stop price for stop orders
            time_in_force: How long order stays active
        
        Returns:
            Order object if successful, None otherwise
        """
        # If qty not specified, sell entire position
        if qty is None:
            position = self.get_position(symbol)
            if position:
                qty = position['qty']
            else:
                logger.error(f"No position to sell for {symbol}")
                return None
        
        return self._place_order(
            symbol=symbol,
            side=OrderSide.SELL,
            qty=qty,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            time_in_force=time_in_force
        )
    
    def _place_order(
        self,
        symbol: str,
        side: OrderSide,
        qty: Optional[int] = None,
        notional: Optional[float] = None,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: TimeInForce = TimeInForce.DAY
    ) -> Optional[Order]:
        """Internal method to place orders"""
        if not self.connected:
            logger.error("Not connected to Alpaca. Cannot place order.")
            return None
        
        if qty is None and notional is None:
            logger.error("Must specify either qty or notional")
            return None
        
        try:
            # Convert enums
            alpaca_side = AlpacaOrderSide.BUY if side == OrderSide.BUY else AlpacaOrderSide.SELL
            alpaca_tif = AlpacaTIF(time_in_force.value)
            
            # Create appropriate order request
            if order_type == OrderType.MARKET:
                if notional:
                    order_data = MarketOrderRequest(
                        symbol=symbol,
                        notional=notional,
                        side=alpaca_side,
                        time_in_force=alpaca_tif
                    )
                else:
                    order_data = MarketOrderRequest(
                        symbol=symbol,
                        qty=qty,
                        side=alpaca_side,
                        time_in_force=alpaca_tif
                    )
            
            elif order_type == OrderType.LIMIT:
                if not limit_price:
                    logger.error("Limit price required for limit orders")
                    return None
                order_data = LimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                    limit_price=limit_price
                )
            
            elif order_type == OrderType.STOP:
                if not stop_price:
                    logger.error("Stop price required for stop orders")
                    return None
                order_data = StopOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                    stop_price=stop_price
                )
            
            elif order_type == OrderType.STOP_LIMIT:
                if not stop_price or not limit_price:
                    logger.error("Stop and limit prices required for stop-limit orders")
                    return None
                order_data = StopLimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=alpaca_side,
                    time_in_force=alpaca_tif,
                    stop_price=stop_price,
                    limit_price=limit_price
                )
            
            else:
                logger.error(f"Unsupported order type: {order_type}")
                return None
            
            # Submit order
            result = self.client.submit_order(order_data)
            
            order = Order(
                symbol=symbol,
                side=side,
                qty=int(result.qty) if result.qty else 0,
                order_type=order_type,
                limit_price=limit_price,
                stop_price=stop_price,
                time_in_force=time_in_force,
                order_id=str(result.id),
                status=OrderStatus(result.status.value),
                filled_qty=int(result.filled_qty) if result.filled_qty else 0,
                filled_avg_price=float(result.filled_avg_price) if result.filled_avg_price else None,
                submitted_at=result.submitted_at
            )
            
            action = "BUY" if side == OrderSide.BUY else "SELL"
            logger.info(f"📈 Order placed: {action} {qty or notional} {symbol} ({order_type.value})")
            logger.info(f"   Order ID: {order.order_id}")
            logger.info(f"   Status: {order.status.value}")
            
            return order
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order"""
        if not self.connected:
            return False
        
        try:
            self.client.cancel_order_by_id(order_id)
            logger.info(f"Order {order_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    def cancel_all_orders(self) -> bool:
        """Cancel all open orders"""
        if not self.connected:
            return False
        
        try:
            self.client.cancel_orders()
            logger.info("All orders cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")
            return False
    
    def get_orders(self, status: str = "open") -> List[Dict]:
        """Get orders by status"""
        if not self.connected:
            return []
        
        try:
            if status == "open":
                query_status = QueryOrderStatus.OPEN
            elif status == "closed":
                query_status = QueryOrderStatus.CLOSED
            else:
                query_status = QueryOrderStatus.ALL
            
            request = GetOrdersRequest(status=query_status)
            orders = self.client.get_orders(request)
            
            return [
                {
                    "order_id": str(order.id),
                    "symbol": order.symbol,
                    "side": order.side.value,
                    "qty": int(order.qty) if order.qty else 0,
                    "type": order.order_type.value,
                    "status": order.status.value,
                    "filled_qty": int(order.filled_qty) if order.filled_qty else 0,
                    "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                    "limit_price": float(order.limit_price) if order.limit_price else None,
                    "stop_price": float(order.stop_price) if order.stop_price else None,
                    "submitted_at": str(order.submitted_at),
                    "filled_at": str(order.filled_at) if order.filled_at else None
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    def close_position(self, symbol: str) -> bool:
        """Close entire position for a symbol"""
        if not self.connected:
            return False
        
        try:
            self.client.close_position(symbol)
            logger.info(f"Position closed: {symbol}")
            return True
        except Exception as e:
            logger.error(f"Error closing position {symbol}: {e}")
            return False
    
    def close_all_positions(self) -> bool:
        """Close all positions"""
        if not self.connected:
            return False
        
        try:
            self.client.close_all_positions(cancel_orders=True)
            logger.info("All positions closed")
            return True
        except Exception as e:
            logger.error(f"Error closing all positions: {e}")
            return False
    
    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        if not self.connected:
            return False
        
        try:
            clock = self.client.get_clock()
            return clock.is_open
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False
    
    def get_market_hours(self) -> Optional[Dict]:
        """Get market hours for today"""
        if not self.connected:
            return None
        
        try:
            clock = self.client.get_clock()
            return {
                "is_open": clock.is_open,
                "next_open": str(clock.next_open),
                "next_close": str(clock.next_close)
            }
        except Exception as e:
            logger.error(f"Error getting market hours: {e}")
            return None


# Create default instance (paper trading)
alpaca_broker = AlpacaBroker(paper=True)
