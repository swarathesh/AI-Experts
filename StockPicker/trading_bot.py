"""
StockPicker Trading Bot
Automated trading based on signals from the analysis engine

⚠️ WARNING: This bot can execute REAL trades if configured with live API keys.
Always test with paper trading first!
"""
import time
import schedule
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger
import sys

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")
logger.add("logs/trading_bot.log", rotation="10 MB", level="DEBUG")

from src.data import market_data
from src.features import indicators
from src.strategies import momentum_strategy, SignalType
from src.broker import AlpacaBroker, OrderType
from src.risk import PositionSizer
from config.settings import settings


class TradingBot:
    """
    Automated Trading Bot
    
    Executes trades based on signals from the momentum strategy.
    Uses Alpaca for order execution (paper trading by default).
    """
    
    def __init__(
        self,
        broker: Optional[AlpacaBroker] = None,
        watchlist: Optional[List[str]] = None,
        max_positions: int = 5,
        position_size_pct: float = 0.10,
        min_confidence: float = 0.6,
        paper: bool = True,
        dry_run: bool = True  # If True, don't actually execute trades
    ):
        """
        Initialize the trading bot
        
        Args:
            broker: AlpacaBroker instance (creates one if not provided)
            watchlist: List of symbols to trade
            max_positions: Maximum number of concurrent positions
            position_size_pct: Position size as fraction of portfolio
            min_confidence: Minimum signal confidence to trade
            paper: Use paper trading (recommended for testing)
            dry_run: If True, simulate trades without executing
        """
        self.broker = broker or AlpacaBroker(paper=paper)
        self.watchlist = watchlist or settings.trading.watchlist
        self.max_positions = max_positions
        self.position_size_pct = position_size_pct
        self.min_confidence = min_confidence
        self.dry_run = dry_run
        
        self.position_sizer = PositionSizer(
            max_position_pct=position_size_pct,
            max_portfolio_risk=0.02
        )
        
        self.running = False
        self.last_scan_time = None
        self.trade_log: List[Dict] = []
        
        if dry_run:
            logger.warning("🔒 DRY RUN MODE - No real trades will be executed")
        else:
            mode = "PAPER" if paper else "⚠️ LIVE"
            logger.info(f"Trading mode: {mode}")
    
    def start(self, scan_interval_minutes: int = 15):
        """
        Start the trading bot
        
        Args:
            scan_interval_minutes: How often to scan for signals
        """
        logger.info("="*50)
        logger.info("  STARTING STOCKPICKER TRADING BOT")
        logger.info("="*50)
        
        if not self.broker.connected and not self.dry_run:
            logger.error("Broker not connected. Set API keys or use dry_run=True")
            return
        
        self.running = True
        
        # Initial scan
        self.run_trading_cycle()
        
        # Schedule regular scans
        schedule.every(scan_interval_minutes).minutes.do(self.run_trading_cycle)
        
        logger.info(f"Bot running. Scanning every {scan_interval_minutes} minutes.")
        logger.info("Press Ctrl+C to stop.\n")
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nBot stopped by user")
            self.stop()
    
    def stop(self):
        """Stop the trading bot"""
        self.running = False
        logger.info("Trading bot stopped")
    
    def run_trading_cycle(self):
        """Run one complete trading cycle"""
        logger.info("-"*40)
        logger.info(f"Running trading cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check if market is open
        if not self.dry_run:
            market_hours = self.broker.get_market_hours()
            if market_hours and not market_hours['is_open']:
                logger.info(f"Market closed. Next open: {market_hours['next_open']}")
                return
        
        # Get account info
        if self.dry_run:
            account = {"buying_power": 100000, "portfolio_value": 100000}
            positions = []
        else:
            account = self.broker.get_account()
            positions = self.broker.get_positions()
        
        if account:
            logger.info(f"Portfolio Value: ${account['portfolio_value']:,.2f}")
            logger.info(f"Buying Power: ${account['buying_power']:,.2f}")
            logger.info(f"Current Positions: {len(positions)}")
        
        # Check for exit signals on existing positions
        for pos in positions:
            self._check_exit_signal(pos)
        
        # Scan for entry signals
        if len(positions) < self.max_positions:
            self._scan_for_entries(account, len(positions))
        else:
            logger.info(f"Max positions ({self.max_positions}) reached. Skipping entry scan.")
        
        self.last_scan_time = datetime.now()
        logger.info("-"*40 + "\n")
    
    def _scan_for_entries(self, account: Dict, current_positions: int):
        """Scan watchlist for entry signals"""
        logger.info(f"Scanning {len(self.watchlist)} stocks for entry signals...")
        
        signals = []
        
        for symbol in self.watchlist:
            try:
                # Fetch data
                df = market_data.get_historical_data(symbol, period="3mo")
                if df.empty or len(df) < 50:
                    continue
                
                # Add indicators
                df = indicators.add_all_indicators(df)
                df = df.dropna()
                
                if len(df) == 0:
                    continue
                
                # Generate signal
                signal = momentum_strategy.analyze(df, symbol)
                
                # Check for buy signals
                if signal.signal in [SignalType.STRONG_BUY, SignalType.BUY]:
                    if signal.confidence >= self.min_confidence:
                        signals.append({
                            "symbol": symbol,
                            "signal": signal.signal,
                            "confidence": signal.confidence,
                            "price": signal.price,
                            "reasons": signal.reasons
                        })
            
            except Exception as e:
                logger.debug(f"Error analyzing {symbol}: {e}")
        
        # Sort by confidence
        signals = sorted(signals, key=lambda x: x['confidence'], reverse=True)
        
        # Execute trades for top signals
        slots_available = self.max_positions - current_positions
        
        for sig in signals[:slots_available]:
            self._execute_buy(sig, account)
    
    def _execute_buy(self, signal: Dict, account: Dict):
        """Execute a buy order"""
        symbol = signal['symbol']
        price = signal['price']
        confidence = signal['confidence']
        
        # Calculate position size
        portfolio_value = account.get('portfolio_value', 100000)
        buying_power = account.get('buying_power', 0)
        
        shares, position_value = self.position_sizer.calculate_position_size(
            portfolio_value=portfolio_value,
            entry_price=price,
            stop_loss_pct=settings.trading.stop_loss_pct
        )
        
        # Check if we have enough buying power
        if position_value > buying_power:
            shares = int(buying_power * 0.95 / price)
            position_value = shares * price
        
        if shares <= 0:
            logger.warning(f"Insufficient funds for {symbol}")
            return
        
        logger.info(f"\n🟢 BUY SIGNAL: {symbol}")
        logger.info(f"   Signal: {signal['signal'].name} (Confidence: {confidence:.1%})")
        logger.info(f"   Price: ${price:.2f}")
        logger.info(f"   Shares: {shares} (${position_value:,.2f})")
        logger.info(f"   Reasons: {', '.join(signal['reasons'][:2])}")
        
        if self.dry_run:
            logger.info("   [DRY RUN] Order would be placed")
            self._log_trade("BUY", symbol, shares, price, "dry_run")
        else:
            order = self.broker.buy(symbol, qty=shares)
            if order:
                self._log_trade("BUY", symbol, shares, price, order.order_id)
    
    def _check_exit_signal(self, position: Dict):
        """Check if we should exit a position"""
        symbol = position['symbol']
        entry_price = position['avg_entry_price']
        current_price = position['current_price']
        unrealized_pnl_pct = position['unrealized_plpc']
        
        should_exit = False
        reason = ""
        
        # Check stop loss
        if unrealized_pnl_pct <= -settings.trading.stop_loss_pct:
            should_exit = True
            reason = f"Stop loss hit ({unrealized_pnl_pct:.1%})"
        
        # Check take profit
        elif unrealized_pnl_pct >= settings.trading.take_profit_pct:
            should_exit = True
            reason = f"Take profit hit ({unrealized_pnl_pct:.1%})"
        
        # Check for sell signal
        else:
            try:
                df = market_data.get_historical_data(symbol, period="3mo")
                if not df.empty and len(df) >= 50:
                    df = indicators.add_all_indicators(df).dropna()
                    if len(df) > 0:
                        signal = momentum_strategy.analyze(df, symbol)
                        if signal.signal in [SignalType.STRONG_SELL, SignalType.SELL]:
                            if signal.confidence >= self.min_confidence:
                                should_exit = True
                                reason = f"Sell signal ({signal.signal.name})"
            except Exception as e:
                logger.debug(f"Error checking exit for {symbol}: {e}")
        
        if should_exit:
            qty = position['qty']
            logger.info(f"\n🔴 SELL SIGNAL: {symbol}")
            logger.info(f"   Reason: {reason}")
            logger.info(f"   Entry: ${entry_price:.2f} → Current: ${current_price:.2f}")
            logger.info(f"   P&L: {unrealized_pnl_pct:.1%}")
            
            if self.dry_run:
                logger.info("   [DRY RUN] Sell order would be placed")
                self._log_trade("SELL", symbol, qty, current_price, "dry_run")
            else:
                order = self.broker.sell(symbol, qty=qty)
                if order:
                    self._log_trade("SELL", symbol, qty, current_price, order.order_id)
    
    def _log_trade(self, action: str, symbol: str, qty: int, price: float, order_id: str):
        """Log a trade"""
        self.trade_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "symbol": symbol,
            "qty": qty,
            "price": price,
            "order_id": order_id
        })
    
    def get_trade_log(self) -> List[Dict]:
        """Get the trade log"""
        return self.trade_log
    
    def manual_buy(self, symbol: str, qty: Optional[int] = None, amount: Optional[float] = None):
        """
        Manually buy a stock
        
        Args:
            symbol: Stock symbol
            qty: Number of shares (optional)
            amount: Dollar amount to invest (optional, used if qty not provided)
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would buy {qty or amount} of {symbol}")
            return
        
        if qty:
            order = self.broker.buy(symbol, qty=qty)
        elif amount:
            order = self.broker.buy(symbol, notional=amount)
        else:
            # Use default position sizing
            account = self.broker.get_account()
            if not account:
                return
            
            df = market_data.get_historical_data(symbol, period="1d")
            if df.empty:
                return
            
            price = df['close'].iloc[-1]
            shares, _ = self.position_sizer.calculate_position_size(
                portfolio_value=account['portfolio_value'],
                entry_price=price
            )
            order = self.broker.buy(symbol, qty=shares)
        
        return order
    
    def manual_sell(self, symbol: str, qty: Optional[int] = None):
        """
        Manually sell a stock
        
        Args:
            symbol: Stock symbol
            qty: Number of shares (optional, sells all if not specified)
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would sell {qty or 'all'} of {symbol}")
            return
        
        return self.broker.sell(symbol, qty=qty)
    
    def show_status(self):
        """Show current bot status"""
        print("\n" + "="*50)
        print("  TRADING BOT STATUS")
        print("="*50)
        
        if self.broker.connected:
            account = self.broker.get_account()
            positions = self.broker.get_positions()
            
            print(f"\n💰 Account:")
            print(f"   Portfolio Value: ${account['portfolio_value']:,.2f}")
            print(f"   Cash: ${account['cash']:,.2f}")
            print(f"   Buying Power: ${account['buying_power']:,.2f}")
            
            print(f"\n📊 Positions ({len(positions)}):")
            if positions:
                for pos in positions:
                    pnl_emoji = "🟢" if pos['unrealized_pl'] >= 0 else "🔴"
                    print(f"   {pos['symbol']:6} | {pos['qty']:>4} shares | "
                          f"${pos['current_price']:>8.2f} | "
                          f"{pnl_emoji} {pos['unrealized_plpc']:>6.1%}")
            else:
                print("   No open positions")
            
            market = self.broker.get_market_hours()
            if market:
                status = "🟢 OPEN" if market['is_open'] else "🔴 CLOSED"
                print(f"\n🕐 Market: {status}")
        
        print(f"\n📝 Trades this session: {len(self.trade_log)}")
        print(f"🔄 Last scan: {self.last_scan_time or 'Never'}")
        print(f"⚙️  Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print("="*50 + "\n")


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("  STOCKPICKER TRADING BOT")
    print("="*60)
    print("\nOptions:")
    print("  1. Run in DRY RUN mode (no real trades)")
    print("  2. Run in PAPER trading mode (simulated with Alpaca)")
    print("  3. Show status only")
    print("  4. Exit")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        bot = TradingBot(dry_run=True)
        bot.start(scan_interval_minutes=15)
    
    elif choice == "2":
        import os
        if not os.getenv("ALPACA_API_KEY"):
            print("\n⚠️  Alpaca API keys not found!")
            print("Set environment variables or create .env file:")
            print("  ALPACA_API_KEY=your_key")
            print("  ALPACA_SECRET_KEY=your_secret")
            return
        
        bot = TradingBot(paper=True, dry_run=False)
        bot.start(scan_interval_minutes=15)
    
    elif choice == "3":
        bot = TradingBot(dry_run=True)
        bot.show_status()
    
    else:
        print("Exiting...")


if __name__ == "__main__":
    main()
