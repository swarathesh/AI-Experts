"""
StockPicker AI Agent - Main Entry Point

This script demonstrates the complete workflow:
1. Fetch market data
2. Calculate technical indicators
3. Train ML models
4. Generate trading signals
5. Backtest strategies
6. Display results
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
import sys

# Configure logging
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")
logger.add("logs/stockpicker.log", rotation="10 MB", level="DEBUG")

from src.data import market_data
from src.features import indicators
from src.models import StockPredictor, SignalGenerator
from src.strategies import momentum_strategy, mean_reversion_strategy, SignalType
from src.backtest import Backtester
from src.risk import PortfolioManager
from config.settings import settings


def fetch_and_prepare_data(symbols: list, period: str = "2y") -> dict:
    """Fetch data and calculate indicators for all symbols"""
    logger.info(f"Fetching data for {len(symbols)} symbols...")
    
    prepared_data = {}
    
    for symbol in symbols:
        try:
            # Fetch historical data
            df = market_data.get_historical_data(symbol, period=period)
            
            if df.empty or len(df) < 50:
                logger.warning(f"Insufficient data for {symbol}")
                continue
            
            # Add technical indicators
            df = indicators.add_all_indicators(df)
            
            # Drop NaN rows
            df = df.dropna()
            
            if len(df) > 0:
                prepared_data[symbol] = df
                logger.debug(f"{symbol}: {len(df)} rows with {len(df.columns)} features")
        
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
    
    logger.info(f"Prepared data for {len(prepared_data)} symbols")
    return prepared_data


def train_ml_model(data: dict) -> StockPredictor:
    """Train the ML ensemble model"""
    logger.info("Training ML model...")
    
    # Combine all data for training
    all_data = []
    for symbol, df in data.items():
        df_copy = df.copy()
        df_copy['symbol'] = symbol
        all_data.append(df_copy)
    
    combined = pd.concat(all_data, ignore_index=True)
    logger.info(f"Combined dataset: {len(combined)} rows")
    
    # Train predictor
    predictor = StockPredictor(prediction_horizon=5)
    X, y = predictor.prepare_features(combined)
    
    if len(X) == 0:
        logger.error("No valid features for training")
        return predictor
    
    metrics = predictor.train(X, y, test_size=0.2)
    
    # Display results
    logger.info("\nModel Performance:")
    for model_name, model_metrics in metrics.items():
        logger.info(f"  {model_name}: Accuracy={model_metrics['accuracy']:.3f}, F1={model_metrics['f1']:.3f}")
    
    return predictor


def generate_signals(data: dict) -> dict:
    """Generate trading signals using momentum strategy"""
    logger.info("\nGenerating trading signals...")
    
    signals = {}
    
    for symbol, df in data.items():
        # Momentum strategy
        momentum_signal = momentum_strategy.analyze(df, symbol)
        
        # Mean reversion strategy
        reversion_signal = mean_reversion_strategy.analyze(df, symbol)
        
        # Combine signals (simple average)
        combined_value = (momentum_signal.signal.value + reversion_signal.signal.value) / 2
        
        signals[symbol] = {
            "momentum": momentum_signal.to_dict(),
            "mean_reversion": reversion_signal.to_dict(),
            "combined_score": combined_value,
            "current_price": df['close'].iloc[-1],
            "return_5d": df['return_5d'].iloc[-1] if 'return_5d' in df else None
        }
    
    return signals


def run_backtest(data: dict) -> None:
    """Run backtest on the momentum strategy"""
    logger.info("\nRunning backtest...")
    
    def signal_func(df: pd.DataFrame, symbol: str) -> int:
        """Signal function for backtester"""
        signal = momentum_strategy.analyze(df, symbol)
        
        if signal.signal in [SignalType.STRONG_BUY, SignalType.BUY]:
            return 1
        elif signal.signal in [SignalType.STRONG_SELL, SignalType.SELL]:
            return -1
        return 0
    
    backtester = Backtester(
        initial_capital=settings.backtest.initial_capital,
        commission=settings.backtest.commission,
        slippage=settings.backtest.slippage,
        stop_loss=settings.trading.stop_loss_pct,
        take_profit=settings.trading.take_profit_pct
    )
    
    results = backtester.run(data, signal_func)
    results.print_summary()
    
    return results


def display_top_picks(signals: dict, top_n: int = 5) -> None:
    """Display top stock picks"""
    print("\n" + "="*60)
    print("TOP STOCK PICKS")
    print("="*60)
    
    # Sort by combined score
    sorted_signals = sorted(
        signals.items(),
        key=lambda x: x[1]['combined_score'],
        reverse=True
    )
    
    # Buy recommendations
    print("\n🟢 BUY RECOMMENDATIONS:")
    print("-"*60)
    
    buy_count = 0
    for symbol, data in sorted_signals:
        if data['combined_score'] > 0.3 and buy_count < top_n:
            mom = data['momentum']
            print(f"\n{symbol} @ ${data['current_price']:.2f}")
            print(f"  Signal: {mom['signal']} (Confidence: {mom['confidence']:.1%})")
            print(f"  Reasons: {', '.join(mom['reasons'][:3])}")
            buy_count += 1
    
    if buy_count == 0:
        print("  No strong buy signals at this time")
    
    # Sell recommendations
    print("\n🔴 SELL/AVOID RECOMMENDATIONS:")
    print("-"*60)
    
    sell_count = 0
    for symbol, data in reversed(sorted_signals):
        if data['combined_score'] < -0.3 and sell_count < top_n:
            mom = data['momentum']
            print(f"\n{symbol} @ ${data['current_price']:.2f}")
            print(f"  Signal: {mom['signal']} (Confidence: {mom['confidence']:.1%})")
            print(f"  Reasons: {', '.join(mom['reasons'][:3])}")
            sell_count += 1
    
    if sell_count == 0:
        print("  No strong sell signals at this time")
    
    print("\n" + "="*60)


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("  STOCKPICKER AI AGENT")
    print("  Intelligent Stock Market Analysis System")
    print("="*60)
    
    # Use watchlist from settings
    symbols = settings.trading.watchlist
    
    # Step 1: Fetch and prepare data
    data = fetch_and_prepare_data(symbols, period="2y")
    
    if not data:
        logger.error("No data available. Exiting.")
        return
    
    # Step 2: Generate signals
    signals = generate_signals(data)
    
    # Step 3: Display recommendations
    display_top_picks(signals, top_n=5)
    
    # Step 4: Run backtest
    backtest_results = run_backtest(data)
    
    # Step 5: Optional - Train ML model
    print("\nWould you like to train the ML model? (This may take a few minutes)")
    print("Skipping ML training for quick demo...")
    
    # Uncomment to train:
    # predictor = train_ml_model(data)
    # predictor.save("models/trained_model")
    
    print("\n✅ Analysis complete!")
    print("Review the signals above and always do your own research before trading.")
    print("⚠️  This is for educational purposes only. Not financial advice.\n")


if __name__ == "__main__":
    main()
