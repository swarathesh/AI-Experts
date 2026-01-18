#!/usr/bin/env python3
"""
StockPicker End-to-End Automation Pipeline

This script automates the complete trading workflow:
1. Market scanning for opportunities
2. Data collection and feature engineering
3. ML model training/loading
4. Signal generation
5. Strategy backtesting
6. Trade execution (paper trading)
7. Portfolio monitoring
8. Reporting and notifications

Usage:
    python run_automation.py --mode [scan|trade|backtest|full]
    python run_automation.py --schedule  # Run on schedule

⚠️ DISCLAIMER: This is for educational purposes only. Not financial advice.
"""
import argparse
import sys
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import schedule
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
logger.add("logs/automation.log", rotation="10 MB", level="DEBUG", retention="30 days")

from config.settings import settings
from src.data import market_data
from src.features import indicators
from src.models import StockPredictor, SignalGenerator
from src.strategies import momentum_strategy, mean_reversion_strategy, SignalType
from src.backtest import Backtester
from src.risk import PortfolioManager, PositionSizer
from src.broker import AlpacaBroker
from scanner import (
    SCAN_UNIVERSE,
    scan_for_breakouts,
    scan_for_oversold,
    scan_for_golden_cross,
    scan_for_macd_crossover,
    scan_for_high_momentum
)


class TradingPipeline:
    """
    End-to-End Trading Automation Pipeline
    
    Orchestrates all components of the trading system.
    """
    
    def __init__(
        self,
        paper_trading: bool = True,
        dry_run: bool = True,
        max_positions: int = 5,
        initial_capital: float = 100_000,
        model_path: Optional[str] = None
    ):
        """
        Initialize the trading pipeline
        
        Args:
            paper_trading: Use paper trading (recommended)
            dry_run: If True, simulate trades without executing
            max_positions: Maximum concurrent positions
            initial_capital: Starting capital for simulation
            model_path: Path to saved ML model (optional)
        """
        self.paper_trading = paper_trading
        self.dry_run = dry_run
        self.max_positions = max_positions
        self.initial_capital = initial_capital
        
        # Initialize components
        self.broker = None
        self.predictor = None
        self.position_sizer = PositionSizer(
            max_position_pct=settings.trading.max_position_size,
            max_portfolio_risk=settings.trading.max_portfolio_risk
        )
        
        # State
        self.market_data: Dict = {}
        self.signals: Dict = {}
        self.scan_results: Dict = {}
        self.trade_log: List = []
        self.last_run: Optional[datetime] = None
        
        # Paths
        self.model_path = model_path or "models/trained_model"
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)
        
        logger.info("="*60)
        logger.info("  STOCKPICKER AUTOMATION PIPELINE")
        logger.info("="*60)
        logger.info(f"Mode: {'Paper Trading' if paper_trading else 'LIVE TRADING'}")
        logger.info(f"Dry Run: {dry_run}")
        logger.info(f"Max Positions: {max_positions}")
        logger.info(f"Initial Capital: ${initial_capital:,.2f}")
        logger.info("="*60 + "\n")
    
    def connect_broker(self) -> bool:
        """Connect to the Alpaca broker"""
        logger.info("Connecting to broker...")
        
        try:
            self.broker = AlpacaBroker(paper=self.paper_trading)
            
            # Broker auto-connects in __init__ if keys are available
            if self.broker.connected:
                account = self.broker.get_account()
                if account:
                    logger.info(f"✅ Connected! Portfolio: ${account['portfolio_value']:,.2f}")
                    return True
                else:
                    logger.warning("Connected but failed to get account info")
            
            if self.dry_run:
                logger.warning("Broker connection failed, but dry_run=True. Continuing with simulation.")
                return True
            
            logger.error("❌ Failed to connect to broker. Check your API keys in .env")
            logger.error("   Make sure ALPACA_API_KEY and ALPACA_SECRET_KEY are set correctly")
            return False
            
        except Exception as e:
            logger.error(f"Broker connection error: {e}")
            if self.dry_run:
                logger.warning("Continuing with dry run mode...")
                return True
            return False
    
    def fetch_market_data(self, symbols: Optional[List[str]] = None, period: str = "1y") -> Dict:
        """
        Fetch and prepare market data for all symbols
        """
        symbols = symbols or SCAN_UNIVERSE
        logger.info(f"\n📊 Fetching market data for {len(symbols)} symbols...")
        
        self.market_data = {}
        success_count = 0
        
        for i, symbol in enumerate(symbols):
            try:
                # Progress indicator
                if (i + 1) % 10 == 0:
                    logger.info(f"  Progress: {i + 1}/{len(symbols)}")
                
                # Fetch historical data
                df = market_data.get_historical_data(symbol, period=period)
                
                if df.empty or len(df) < 50:
                    logger.debug(f"Insufficient data for {symbol}")
                    continue
                
                # Add technical indicators
                df = indicators.add_all_indicators(df)
                df = df.dropna()
                
                if len(df) > 0:
                    self.market_data[symbol] = df
                    success_count += 1
                    
            except Exception as e:
                logger.debug(f"Error fetching {symbol}: {e}")
        
        logger.info(f"✅ Fetched data for {success_count}/{len(symbols)} symbols\n")
        return self.market_data
    
    def run_market_scan(self) -> Dict:
        """
        Run all market scans to find opportunities
        """
        logger.info("🔍 Running market scans...")
        
        if not self.market_data:
            self.fetch_market_data()
        
        self.scan_results = {
            "breakouts": scan_for_breakouts(self.market_data),
            "oversold": scan_for_oversold(self.market_data),
            "golden_cross": scan_for_golden_cross(self.market_data),
            "macd_crossover": scan_for_macd_crossover(self.market_data),
            "high_momentum": scan_for_high_momentum(self.market_data)
        }
        
        # Log results
        for scan_name, results in self.scan_results.items():
            if results:
                logger.info(f"  {scan_name}: {len(results)} opportunities found")
        
        return self.scan_results
    
    def generate_signals(self) -> Dict:
        """
        Generate trading signals for all symbols
        """
        logger.info("\n📈 Generating trading signals...")
        
        if not self.market_data:
            self.fetch_market_data()
        
        self.signals = {}
        buy_signals = 0
        sell_signals = 0
        
        for symbol, df in self.market_data.items():
            try:
                # Get signals from multiple strategies
                momentum_signal = momentum_strategy.analyze(df, symbol)
                reversion_signal = mean_reversion_strategy.analyze(df, symbol)
                
                # Combine signals
                combined_score = (momentum_signal.signal.value + reversion_signal.signal.value) / 2
                avg_confidence = (momentum_signal.confidence + reversion_signal.confidence) / 2
                
                # Determine action
                if combined_score > 0.5 and avg_confidence > settings.model.min_confidence:
                    action = "BUY"
                    buy_signals += 1
                elif combined_score < -0.5 and avg_confidence > settings.model.min_confidence:
                    action = "SELL"
                    sell_signals += 1
                else:
                    action = "HOLD"
                
                self.signals[symbol] = {
                    "action": action,
                    "momentum_signal": momentum_signal.signal.name,
                    "reversion_signal": reversion_signal.signal.name,
                    "combined_score": combined_score,
                    "confidence": avg_confidence,
                    "price": df['close'].iloc[-1],
                    "reasons": momentum_signal.reasons[:3]
                }
                
            except Exception as e:
                logger.debug(f"Error generating signal for {symbol}: {e}")
        
        logger.info(f"✅ Generated signals: {buy_signals} BUY, {sell_signals} SELL, {len(self.signals) - buy_signals - sell_signals} HOLD\n")
        return self.signals
    
    def train_model(self, save: bool = True) -> StockPredictor:
        """
        Train the ML ensemble model
        """
        logger.info("\n🤖 Training ML model...")
        
        if not self.market_data:
            self.fetch_market_data()
        
        # Combine all data
        import pandas as pd
        all_data = []
        for symbol, df in self.market_data.items():
            df_copy = df.copy()
            df_copy['symbol'] = symbol
            all_data.append(df_copy)
        
        combined = pd.concat(all_data, ignore_index=True)
        logger.info(f"Training data: {len(combined)} rows from {len(self.market_data)} symbols")
        
        # Train predictor
        self.predictor = StockPredictor(prediction_horizon=5)
        X, y = self.predictor.prepare_features(combined)
        
        if len(X) == 0:
            logger.error("No valid features for training")
            return self.predictor
        
        metrics = self.predictor.train(X, y, test_size=0.2)
        
        # Log performance
        logger.info("Model Performance:")
        for model_name, model_metrics in metrics.items():
            logger.info(f"  {model_name}: Accuracy={model_metrics['accuracy']:.3f}, F1={model_metrics['f1']:.3f}")
        
        # Save model
        if save:
            Path(self.model_path).parent.mkdir(exist_ok=True)
            self.predictor.save(self.model_path)
            logger.info(f"✅ Model saved to {self.model_path}")
        
        return self.predictor
    
    def run_backtest(self) -> None:
        """
        Run backtest on the trading strategy
        """
        logger.info("\n📉 Running backtest...")
        
        if not self.market_data:
            self.fetch_market_data()
        
        def signal_func(df, symbol):
            signal = momentum_strategy.analyze(df, symbol)
            if signal.signal in [SignalType.STRONG_BUY, SignalType.BUY]:
                return 1
            elif signal.signal in [SignalType.STRONG_SELL, SignalType.SELL]:
                return -1
            return 0
        
        backtester = Backtester(
            initial_capital=self.initial_capital,
            commission=settings.backtest.commission,
            slippage=settings.backtest.slippage,
            stop_loss=settings.trading.stop_loss_pct,
            take_profit=settings.trading.take_profit_pct
        )
        
        results = backtester.run(self.market_data, signal_func)
        results.print_summary()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.results_dir / f"backtest_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results.to_dict(), f, indent=2, default=str)
        
        logger.info(f"✅ Results saved to {results_file}")
        return results
    
    def get_top_picks(self, n: int = 5) -> List[Dict]:
        """
        Get top n buy recommendations
        """
        if not self.signals:
            self.generate_signals()
        
        # Filter and sort by confidence
        buy_signals = [
            {"symbol": sym, **data}
            for sym, data in self.signals.items()
            if data['action'] == "BUY"
        ]
        
        return sorted(buy_signals, key=lambda x: x['confidence'], reverse=True)[:n]
    
    def execute_trades(self) -> List[Dict]:
        """
        Execute trades based on signals
        """
        logger.info("\n💰 Executing trades...")
        
        if not self.signals:
            self.generate_signals()
        
        # Get account info
        if self.dry_run or not self.broker or not self.broker.connected:
            account = {"buying_power": self.initial_capital, "portfolio_value": self.initial_capital}
            positions = []
            if not self.dry_run:
                logger.warning("Broker not connected - falling back to simulation mode")
        else:
            account = self.broker.get_account()
            positions = self.broker.get_positions() or []
            
            # Handle failed account fetch
            if account is None:
                logger.error("Failed to get account info from broker")
                logger.warning("Falling back to simulation mode")
                account = {"buying_power": self.initial_capital, "portfolio_value": self.initial_capital}
                positions = []
        
        current_positions = len(positions)
        slots_available = self.max_positions - current_positions
        
        logger.info(f"Current positions: {current_positions}/{self.max_positions}")
        logger.info(f"Portfolio value: ${account['portfolio_value']:,.2f}")
        logger.info(f"Buying power: ${account['buying_power']:,.2f}")
        
        # Get top picks
        top_picks = self.get_top_picks(slots_available)
        
        executed_trades = []
        
        for pick in top_picks:
            symbol = pick['symbol']
            price = pick['price']
            confidence = pick['confidence']
            
            # Calculate position size
            shares, position_value = self.position_sizer.calculate_position_size(
                portfolio_value=account['portfolio_value'],
                entry_price=price,
                stop_loss_pct=settings.trading.stop_loss_pct
            )
            
            if shares <= 0:
                continue
            
            trade = {
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "action": "BUY",
                "shares": shares,
                "price": price,
                "value": position_value,
                "confidence": confidence,
                "reasons": pick['reasons'],
                "status": "simulated" if self.dry_run else "pending"
            }
            
            logger.info(f"\n🟢 {symbol}: BUY {shares} shares @ ${price:.2f} (${position_value:,.2f})")
            logger.info(f"   Confidence: {confidence:.1%}")
            logger.info(f"   Reasons: {', '.join(pick['reasons'][:2])}")
            
            if self.dry_run:
                trade["status"] = "simulated"
                logger.info("   [DRY RUN] Trade simulated")
            else:
                try:
                    order = self.broker.buy(symbol, qty=shares)
                    if order:
                        trade["status"] = "executed"
                        trade["order_id"] = order.order_id
                        logger.info(f"   ✅ Order placed: {order.order_id}")
                    else:
                        trade["status"] = "failed"
                        logger.error(f"   ❌ Order failed")
                except Exception as e:
                    trade["status"] = "error"
                    trade["error"] = str(e)
                    logger.error(f"   ❌ Error: {e}")
            
            executed_trades.append(trade)
            self.trade_log.append(trade)
        
        return executed_trades
    
    def generate_report(self) -> Dict:
        """
        Generate a comprehensive report
        """
        logger.info("\n📋 Generating report...")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "market_data_symbols": len(self.market_data),
            "signals_generated": len(self.signals),
            "scan_results": {k: len(v) for k, v in self.scan_results.items()},
            "top_picks": self.get_top_picks(10),
            "trades_executed": len(self.trade_log),
            "trade_log": self.trade_log
        }
        
        # Print summary
        print("\n" + "="*60)
        print("  TRADING REPORT")
        print("="*60)
        print(f"Generated: {report['timestamp']}")
        print(f"Symbols analyzed: {report['market_data_symbols']}")
        print(f"Signals generated: {report['signals_generated']}")
        print(f"Trades executed: {report['trades_executed']}")
        
        print("\n🔍 SCAN RESULTS:")
        for scan, count in report['scan_results'].items():
            print(f"  {scan}: {count} opportunities")
        
        print("\n🏆 TOP PICKS:")
        for i, pick in enumerate(report['top_picks'][:5], 1):
            print(f"  {i}. {pick['symbol']} @ ${pick['price']:.2f} ({pick['confidence']:.1%})")
        
        print("="*60 + "\n")
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.results_dir / f"report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"✅ Report saved to {report_file}")
        
        return report
    
    def run_full_pipeline(self) -> Dict:
        """
        Run the complete end-to-end pipeline
        """
        logger.info("\n🚀 Running full automation pipeline...\n")
        start_time = datetime.now()
        
        # Step 1: Connect to broker
        self.connect_broker()
        
        # Step 2: Fetch market data
        self.fetch_market_data()
        
        # Step 3: Run market scans
        self.run_market_scan()
        
        # Step 4: Generate signals
        self.generate_signals()
        
        # Step 5: Run backtest
        self.run_backtest()
        
        # Step 6: Execute trades
        self.execute_trades()
        
        # Step 7: Generate report
        report = self.generate_report()
        
        elapsed = datetime.now() - start_time
        logger.info(f"\n⏱️ Pipeline completed in {elapsed.total_seconds():.1f} seconds")
        
        self.last_run = datetime.now()
        
        return report


def run_scheduled_job(pipeline: TradingPipeline):
    """Job to run on schedule"""
    logger.info(f"\n⏰ Scheduled run at {datetime.now()}")
    
    # Check if market is open (simplified check)
    now = datetime.now()
    weekday = now.weekday()
    hour = now.hour
    
    # Skip weekends
    if weekday >= 5:
        logger.info("Weekend - skipping")
        return
    
    # Only run during market hours (9:30 AM - 4:00 PM ET approximately)
    if hour < 9 or hour >= 16:
        logger.info("Outside market hours - skipping")
        return
    
    pipeline.run_full_pipeline()


def main():
    parser = argparse.ArgumentParser(
        description="StockPicker End-to-End Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_automation.py --mode scan          # Run market scan only
  python run_automation.py --mode signals       # Generate trading signals
  python run_automation.py --mode backtest      # Run strategy backtest
  python run_automation.py --mode trade         # Execute trades (dry run)
  python run_automation.py --mode full          # Run complete pipeline
  python run_automation.py --schedule           # Run on hourly schedule
  python run_automation.py --mode trade --execute  # Execute REAL paper trades
  python run_automation.py --mode full --live   # ⚠️ Real trading (dangerous!)
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["scan", "signals", "backtest", "trade", "train", "full"],
        default="full",
        help="Automation mode to run"
    )
    
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run on schedule (every hour during market hours)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Simulate trades without executing (default: True)"
    )
    
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute real paper trades (disables dry-run for paper trading)"
    )
    
    parser.add_argument(
        "--live",
        action="store_true",
        help="⚠️ DANGER: Enable live trading with real money"
    )
    
    parser.add_argument(
        "--max-positions",
        type=int,
        default=5,
        help="Maximum number of concurrent positions"
    )
    
    parser.add_argument(
        "--capital",
        type=float,
        default=100000,
        help="Initial capital for simulation"
    )
    
    args = parser.parse_args()
    
    # Safety check for live trading
    if args.live:
        print("\n" + "⚠️"*20)
        print("WARNING: You are about to enable LIVE TRADING!")
        print("Real money will be at risk.")
        print("⚠️"*20 + "\n")
        
        confirm = input("Type 'I UNDERSTAND THE RISKS' to continue: ")
        if confirm != "I UNDERSTAND THE RISKS":
            print("Aborting.")
            sys.exit(1)
    
    # Determine dry_run mode
    # --execute flag disables dry_run for paper trading
    # --live flag enables live trading (not paper)
    if args.live:
        dry_run = False
        paper_trading = False
    elif args.execute:
        dry_run = False
        paper_trading = True
        print("\n📝 PAPER TRADING MODE - Real orders will be placed on Alpaca paper account\n")
    else:
        dry_run = True
        paper_trading = True
    
    # Initialize pipeline
    pipeline = TradingPipeline(
        paper_trading=paper_trading,
        dry_run=dry_run,
        max_positions=args.max_positions,
        initial_capital=args.capital
    )
    
    if args.schedule:
        # Run on schedule
        logger.info("Starting scheduled automation...")
        logger.info("Will run every hour during market hours")
        logger.info("Press Ctrl+C to stop\n")
        
        # Run immediately
        run_scheduled_job(pipeline)
        
        # Then schedule hourly
        schedule.every(1).hours.do(run_scheduled_job, pipeline)
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("\nScheduler stopped")
    
    else:
        # Run specific mode
        mode = args.mode
        
        if mode == "scan":
            pipeline.fetch_market_data()
            results = pipeline.run_market_scan()
            
            print("\n" + "="*50)
            for scan_name, opportunities in results.items():
                print(f"\n{scan_name.upper()}:")
                for opp in opportunities[:3]:
                    print(f"  {opp['symbol']}: {opp.get('pattern', 'N/A')} (Score: {opp.get('score', 0):.2f})")
        
        elif mode == "signals":
            pipeline.fetch_market_data()
            signals = pipeline.generate_signals()
            picks = pipeline.get_top_picks(10)
            
            print("\n🏆 TOP 10 BUY SIGNALS:")
            for i, pick in enumerate(picks, 1):
                print(f"{i}. {pick['symbol']} @ ${pick['price']:.2f} - Confidence: {pick['confidence']:.1%}")
        
        elif mode == "backtest":
            pipeline.fetch_market_data()
            pipeline.run_backtest()
        
        elif mode == "train":
            pipeline.fetch_market_data()
            pipeline.train_model(save=True)
        
        elif mode == "trade":
            pipeline.connect_broker()
            pipeline.fetch_market_data()
            pipeline.generate_signals()
            trades = pipeline.execute_trades()
            
            print(f"\n✅ Executed {len(trades)} trades")
        
        elif mode == "full":
            pipeline.run_full_pipeline()
    
    print("\n✅ Automation complete!")
    print("⚠️ This is for educational purposes only. Not financial advice.\n")


if __name__ == "__main__":
    main()
