"""
Real-time Market Data Streaming
WebSocket connections for live price updates
"""
import asyncio
import json
import threading
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set
from dataclasses import dataclass
from loguru import logger
import queue

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logger.warning("websockets not available. Install with: pip install websockets")


@dataclass
class Quote:
    """Real-time quote data"""
    symbol: str
    price: float
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    volume: int
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "bid": self.bid,
            "ask": self.ask,
            "bid_size": self.bid_size,
            "ask_size": self.ask_size,
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class Trade:
    """Real-time trade data"""
    symbol: str
    price: float
    size: int
    timestamp: datetime
    exchange: str
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "size": self.size,
            "timestamp": self.timestamp.isoformat(),
            "exchange": self.exchange
        }


class AlpacaStreamClient:
    """
    Alpaca WebSocket streaming client for real-time market data
    
    Requires Alpaca API keys with market data subscription
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        feed: str = "iex"  # "iex" (free) or "sip" (paid, all exchanges)
    ):
        import os
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")
        self.feed = feed
        
        self.ws = None
        self.running = False
        self.subscribed_symbols: Set[str] = set()
        
        # Callbacks
        self.on_quote: Optional[Callable[[Quote], None]] = None
        self.on_trade: Optional[Callable[[Trade], None]] = None
        self.on_bar: Optional[Callable[[Dict], None]] = None
        
        # Message queue for thread-safe access
        self.quote_queue: queue.Queue = queue.Queue()
        self.trade_queue: queue.Queue = queue.Queue()
        
        # Latest prices cache
        self.latest_prices: Dict[str, float] = {}
        self.latest_quotes: Dict[str, Quote] = {}
        
        # WebSocket URL
        self.ws_url = f"wss://stream.data.alpaca.markets/v2/{feed}"
    
    async def _connect(self):
        """Establish WebSocket connection"""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("websockets library not available")
            return
        
        if not self.api_key or not self.secret_key:
            logger.error("Alpaca API keys not configured")
            return
        
        try:
            self.ws = await websockets.connect(self.ws_url)
            logger.info(f"Connected to Alpaca stream ({self.feed})")
            
            # Authenticate
            auth_msg = {
                "action": "auth",
                "key": self.api_key,
                "secret": self.secret_key
            }
            await self.ws.send(json.dumps(auth_msg))
            
            response = await self.ws.recv()
            data = json.loads(response)
            
            if data[0].get('msg') == 'authenticated':
                logger.info("Authenticated with Alpaca stream")
            else:
                logger.error(f"Authentication failed: {data}")
                return
            
            self.running = True
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.running = False
    
    async def subscribe(self, symbols: List[str], trades: bool = True, quotes: bool = True, bars: bool = False):
        """
        Subscribe to market data for symbols
        
        Args:
            symbols: List of stock symbols
            trades: Subscribe to trade updates
            quotes: Subscribe to quote updates
            bars: Subscribe to minute bars
        """
        if not self.ws:
            await self._connect()
        
        if not self.running:
            logger.error("Not connected to stream")
            return
        
        try:
            sub_msg = {"action": "subscribe"}
            
            if trades:
                sub_msg["trades"] = symbols
            if quotes:
                sub_msg["quotes"] = symbols
            if bars:
                sub_msg["bars"] = symbols
            
            await self.ws.send(json.dumps(sub_msg))
            self.subscribed_symbols.update(symbols)
            
            logger.info(f"Subscribed to: {symbols}")
            
        except Exception as e:
            logger.error(f"Subscription error: {e}")
    
    async def unsubscribe(self, symbols: List[str]):
        """Unsubscribe from symbols"""
        if not self.ws:
            return
        
        try:
            unsub_msg = {
                "action": "unsubscribe",
                "trades": symbols,
                "quotes": symbols,
                "bars": symbols
            }
            await self.ws.send(json.dumps(unsub_msg))
            self.subscribed_symbols -= set(symbols)
            
            logger.info(f"Unsubscribed from: {symbols}")
            
        except Exception as e:
            logger.error(f"Unsubscribe error: {e}")
    
    async def _listen(self):
        """Listen for incoming messages"""
        while self.running and self.ws:
            try:
                message = await asyncio.wait_for(self.ws.recv(), timeout=30)
                data = json.loads(message)
                
                for item in data:
                    msg_type = item.get('T')
                    
                    if msg_type == 't':  # Trade
                        trade = Trade(
                            symbol=item['S'],
                            price=item['p'],
                            size=item['s'],
                            timestamp=datetime.fromisoformat(item['t'].replace('Z', '+00:00')),
                            exchange=item.get('x', 'unknown')
                        )
                        self.latest_prices[trade.symbol] = trade.price
                        self.trade_queue.put(trade)
                        
                        if self.on_trade:
                            self.on_trade(trade)
                    
                    elif msg_type == 'q':  # Quote
                        quote = Quote(
                            symbol=item['S'],
                            price=(item['bp'] + item['ap']) / 2,
                            bid=item['bp'],
                            ask=item['ap'],
                            bid_size=item['bs'],
                            ask_size=item['as'],
                            volume=0,
                            timestamp=datetime.fromisoformat(item['t'].replace('Z', '+00:00'))
                        )
                        self.latest_quotes[quote.symbol] = quote
                        self.quote_queue.put(quote)
                        
                        if self.on_quote:
                            self.on_quote(quote)
                    
                    elif msg_type == 'b':  # Bar
                        bar = {
                            "symbol": item['S'],
                            "open": item['o'],
                            "high": item['h'],
                            "low": item['l'],
                            "close": item['c'],
                            "volume": item['v'],
                            "timestamp": item['t']
                        }
                        if self.on_bar:
                            self.on_bar(bar)
                
            except asyncio.TimeoutError:
                # Send heartbeat
                if self.ws:
                    await self.ws.ping()
            except Exception as e:
                logger.error(f"Stream error: {e}")
                if not self.running:
                    break
                # Attempt reconnection
                await asyncio.sleep(5)
                await self._connect()
    
    async def start(self, symbols: List[str]):
        """Start streaming for symbols"""
        await self._connect()
        if self.running:
            await self.subscribe(symbols)
            await self._listen()
    
    async def stop(self):
        """Stop streaming"""
        self.running = False
        if self.ws:
            await self.ws.close()
            self.ws = None
        logger.info("Stream stopped")
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get the latest price for a symbol"""
        return self.latest_prices.get(symbol)
    
    def get_latest_quote(self, symbol: str) -> Optional[Quote]:
        """Get the latest quote for a symbol"""
        return self.latest_quotes.get(symbol)


class RealtimeMonitor:
    """
    Real-time price monitor with alerts
    Runs in background thread
    """
    
    def __init__(self):
        self.stream_client = AlpacaStreamClient()
        self.price_alerts: Dict[str, List[Dict]] = {}  # symbol -> list of alerts
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Set up callbacks
        self.stream_client.on_trade = self._handle_trade
        self.stream_client.on_quote = self._handle_quote
    
    def add_price_alert(
        self,
        symbol: str,
        price: float,
        direction: str,  # "above" or "below"
        callback: Optional[Callable[[str, float, str], None]] = None
    ):
        """
        Add a price alert
        
        Args:
            symbol: Stock symbol
            price: Target price
            direction: "above" or "below"
            callback: Function to call when alert triggers
        """
        if symbol not in self.price_alerts:
            self.price_alerts[symbol] = []
        
        self.price_alerts[symbol].append({
            "price": price,
            "direction": direction,
            "callback": callback,
            "triggered": False
        })
        
        logger.info(f"Alert added: {symbol} {direction} ${price}")
    
    def _handle_trade(self, trade: Trade):
        """Handle incoming trade"""
        self._check_alerts(trade.symbol, trade.price)
    
    def _handle_quote(self, quote: Quote):
        """Handle incoming quote"""
        self._check_alerts(quote.symbol, quote.price)
    
    def _check_alerts(self, symbol: str, price: float):
        """Check if any alerts should trigger"""
        if symbol not in self.price_alerts:
            return
        
        for alert in self.price_alerts[symbol]:
            if alert['triggered']:
                continue
            
            should_trigger = False
            if alert['direction'] == 'above' and price >= alert['price']:
                should_trigger = True
            elif alert['direction'] == 'below' and price <= alert['price']:
                should_trigger = True
            
            if should_trigger:
                alert['triggered'] = True
                logger.info(f"🔔 ALERT: {symbol} is now ${price:.2f} ({alert['direction']} ${alert['price']})")
                
                if alert['callback']:
                    try:
                        alert['callback'](symbol, price, alert['direction'])
                    except Exception as e:
                        logger.error(f"Alert callback error: {e}")
    
    def start(self, symbols: List[str]):
        """Start monitoring in background thread"""
        if self.running:
            logger.warning("Monitor already running")
            return
        
        def run_async():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self.running = True
            
            try:
                self._loop.run_until_complete(self.stream_client.start(symbols))
            except Exception as e:
                logger.error(f"Monitor error: {e}")
            finally:
                self.running = False
        
        self._thread = threading.Thread(target=run_async, daemon=True)
        self._thread.start()
        logger.info(f"Real-time monitor started for {symbols}")
    
    def stop(self):
        """Stop monitoring"""
        if self._loop and self.running:
            asyncio.run_coroutine_threadsafe(self.stream_client.stop(), self._loop)
        self.running = False
        logger.info("Real-time monitor stopped")
    
    def get_price(self, symbol: str) -> Optional[float]:
        """Get latest price for a symbol"""
        return self.stream_client.get_latest_price(symbol)


# Create instance
realtime_monitor = RealtimeMonitor()
