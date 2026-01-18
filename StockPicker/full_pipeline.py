"""
Full End-to-End Trading Pipeline
Integrates all components: Data, Sentiment, Models, Optimization, Execution, Alerts
"""
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
from loguru import logger
import schedule

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Import all components
from src.data import market_data, sentiment_analyzer, earnings_calendar, realtime_monitor
from src.features import indicators
from src.models import predictor, lstm_predictor, hybrid_ensemble
from src.strategies import momentum_strategy, mean_reversion_strategy
from src.risk import portfolio_manager, position_sizer, portfolio_optimizer
from src.broker import alpaca_broker, OrderSide, OrderType
from src.alerts import notification_manager, AlertType, AlertPriority


@dataclass
class StockAnalysis:
    """Complete analysis for a stock"""
    symbol: str
    price: float
    technical_score: float  # -1 to 1
    ml_score: float  # -1 to 1
    sentiment_score: float  # -1 to 1
    combined_score: float  # -1 to 1
    signal: str  # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    confidence: float  # 0 to 1
    recommended_action: str
    position_size: int
    reasons: List[str]
    earnings_risk: str
    stop_loss: float
    take_profit: float


class TradingPipeline:
    """
    Complete end-to-end trading pipeline
    
    Workflow:
    1. Fetch market data
    2. Calculate technical indicators
    3. Run ML predictions (ensemble + LSTM)
    4. Analyze sentiment (news + social)
    5. Check earnings calendar for risk
    6. Generate trading signals
    7. Optimize portfolio allocation
    8. Execute trades via broker
    9. Send alerts and notifications
    """
    
    def __init__(
        self,
        symbols: List[str],
        portfolio_value: float = 100000,
        max_position_pct: float = 0.10,
        min_confidence: float = 0.6,
        use_sentiment: bool = True,
        use_deep_learning: bool = False,  # Set to True when models are trained
        dry_run: bool = True,
        paper_trading: bool = True
    ):
        """
        Initialize the trading pipeline
        
        Args:
            symbols: List of stock symbols to trade
            portfolio_value: Total portfolio value
            max_position_pct: Maximum position size as % of portfolio
            min_confidence: Minimum confidence to execute trades
            use_sentiment: Whether to incorporate sentiment analysis
            use_deep_learning: Whether to use LSTM/Transformer models
            dry_run: If True, don't execute real trades
            paper_trading: Use paper trading account
        """
        self.symbols = symbols
        self.portfolio_value = portfolio_value
        self.max_position_pct = max_position_pct
        self.min_confidence = min_confidence
        self.use_sentiment = use_sentiment
        self.use_deep_learning = use_deep_learning
        self.dry_run = dry_run
        self.paper_trading = paper_trading
        
        # Component weights for combined score
        self.weights = {
            'technical': 0.35,
            'ml': 0.35,
            'sentiment': 0.30
        }
        
        # If not using sentiment, redistribute weight
        if not use_sentiment:
            self.weights['technical'] = 0.50
            self.weights['ml'] = 0.50
            self.weights['sentiment'] = 0.0
        
        # Cache for data
        self._data_cache: Dict[str, pd.DataFrame] = {}
        self._last_update: Optional[datetime] = None
        
        logger.info(f"Trading Pipeline initialized for {len(symbols)} symbols")
        logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'} | Paper: {paper_trading}")
    
    def analyze_stock(self, symbol: str) -> Optional[StockAnalysis]:
        """
        Perform complete analysis on a single stock
        
        Args:
            symbol: Stock ticker
        
        Returns:
            StockAnalysis object with all scores and recommendations
        """
        reasons = []
        
        try:
            # Step 1: Fetch data
            logger.info(f"Analyzing {symbol}...")
            df = market_data.get_historical_data(symbol, period="1y")
            
            if df is None or len(df) < 50:
                logger.warning(f"Insufficient data for {symbol}")
                return None
            
            current_price = df['close'].iloc[-1]
            
            # Step 2: Technical Analysis
            df_tech = indicators.add_all_indicators(df)
            tech_signal = momentum_strategy.analyze(df_tech, symbol)
            technical_score = self._signal_to_score(tech_signal)
            reasons.append(f"Technical: {tech_signal.signal.value}")
            
            # Step 3: ML Predictions
            try:
                ml_result = predictor.predict(df_tech)
                ml_score = ml_result.get('prediction', 0)
                ml_confidence = ml_result.get('confidence', 0.5)
                reasons.append(f"ML Prediction: {ml_score:.2f} (conf: {ml_confidence:.0%})")
            except Exception as e:
                logger.debug(f"ML prediction failed for {symbol}: {e}")
                ml_score = 0
                ml_confidence = 0.5
            
            # Step 4: Deep Learning (if enabled and trained)
            if self.use_deep_learning and lstm_predictor.is_fitted:
                try:
                    directions, dl_conf = lstm_predictor.predict_direction(df_tech)
                    if len(directions) > 0:
                        dl_score = (directions[-1] * 2) - 1  # Convert 0/1 to -1/1
                        ml_score = (ml_score + dl_score) / 2
                        reasons.append(f"LSTM: {'UP' if dl_score > 0 else 'DOWN'}")
                except Exception as e:
                    logger.debug(f"LSTM failed for {symbol}: {e}")
            
            # Step 5: Sentiment Analysis
            sentiment_score = 0
            if self.use_sentiment:
                try:
                    sentiment = sentiment_analyzer.get_combined_sentiment(symbol)
                    sentiment_score = sentiment['combined_sentiment']
                    reasons.append(f"Sentiment: {sentiment['combined_label']} ({sentiment_score:.2f})")
                except Exception as e:
                    logger.debug(f"Sentiment failed for {symbol}: {e}")
            
            # Step 6: Earnings Risk Check
            try:
                earnings = earnings_calendar.get_upcoming_earnings(symbol)
                earnings_risk = earnings.get('earnings_risk', 'unknown')
                if earnings['next_earnings_date']:
                    days = earnings.get('days_until_earnings')
                    if days and days <= 7:
                        reasons.append(f"⚠️ Earnings in {days} days!")
            except Exception as e:
                logger.debug(f"Earnings check failed for {symbol}: {e}")
                earnings_risk = 'unknown'
            
            # Step 7: Calculate Combined Score
            combined_score = (
                technical_score * self.weights['technical'] +
                ml_score * self.weights['ml'] +
                sentiment_score * self.weights['sentiment']
            )
            
            # Step 8: Generate Signal
            signal, confidence = self._score_to_signal(combined_score)
            
            # Step 9: Determine Action (use same thresholds as signal)
            if confidence >= self.min_confidence:
                if combined_score >= 0.10:
                    action = "BUY"
                elif combined_score <= -0.10:
                    action = "SELL"
                else:
                    action = "HOLD"
            else:
                # Still show signal direction even with low confidence
                if combined_score >= 0.10:
                    action = "BUY (low conf)"
                elif combined_score <= -0.10:
                    action = "SELL (low conf)"
                else:
                    action = "HOLD"
            
            # Step 10: Position Sizing
            volatility = df['close'].pct_change().std() * np.sqrt(252)
            position_size, _ = position_sizer.calculate_position_size(
                portfolio_value=self.portfolio_value,
                entry_price=current_price,
                volatility=volatility
            )
            
            # Cap at max position
            max_shares = int((self.portfolio_value * self.max_position_pct) / current_price)
            position_size = min(position_size, max_shares)
            
            # Step 11: Risk Levels
            atr = df_tech['atr_14'].iloc[-1] if 'atr_14' in df_tech else current_price * 0.02
            stop_loss = current_price - (2 * atr)
            take_profit = current_price + (3 * atr)
            
            return StockAnalysis(
                symbol=symbol,
                price=current_price,
                technical_score=technical_score,
                ml_score=ml_score,
                sentiment_score=sentiment_score,
                combined_score=combined_score,
                signal=signal,
                confidence=confidence,
                recommended_action=action,
                position_size=position_size,
                reasons=reasons,
                earnings_risk=earnings_risk,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
        except Exception as e:
            logger.error(f"Analysis failed for {symbol}: {e}")
            return None
    
    def run_scan(self) -> List[StockAnalysis]:
        """
        Run analysis on all symbols
        
        Returns:
            List of StockAnalysis objects sorted by combined score
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"  RUNNING MARKET SCAN - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"{'='*60}")
        
        analyses = []
        
        for symbol in self.symbols:
            analysis = self.analyze_stock(symbol)
            if analysis:
                analyses.append(analysis)
        
        # Sort by combined score
        analyses.sort(key=lambda x: x.combined_score, reverse=True)
        
        self._last_update = datetime.now()
        
        # Print summary
        self._print_scan_summary(analyses)
        
        return analyses
    
    def _print_scan_summary(self, analyses: List[StockAnalysis]):
        """Print a summary of the scan results"""
        print("\n" + "="*80)
        print(f"  MARKET SCAN RESULTS - {len(analyses)} stocks analyzed")
        print("="*80)
        print(f"{'Symbol':<8} {'Price':>10} {'Tech':>7} {'ML':>7} {'Sent':>7} {'Score':>7} {'Signal':<12} {'Action':<10}")
        print("-"*80)
        
        for a in analyses[:20]:  # Top 20
            print(f"{a.symbol:<8} ${a.price:>8.2f} {a.technical_score:>+6.2f} {a.ml_score:>+6.2f} "
                  f"{a.sentiment_score:>+6.2f} {a.combined_score:>+6.2f} {a.signal:<12} {a.recommended_action:<10}")
        
        print("="*80)
        
        # Highlight top picks
        buys = [a for a in analyses if "BUY" in a.recommended_action and "low" not in a.recommended_action]
        sells = [a for a in analyses if "SELL" in a.recommended_action and "low" not in a.recommended_action]
        
        if buys:
            print(f"\n🟢 TOP BUY SIGNALS: {', '.join([f'{a.symbol} ({a.confidence:.0%})' for a in buys[:5]])}")
        if sells:
            print(f"🔴 TOP SELL SIGNALS: {', '.join([f'{a.symbol} ({a.confidence:.0%})' for a in sells[:5]])}")
        print()
    
    def optimize_portfolio(self, analyses: List[StockAnalysis]) -> Dict[str, float]:
        """
        Run portfolio optimization on analyzed stocks
        
        Args:
            analyses: List of stock analyses
        
        Returns:
            Dictionary of symbol -> optimal weight
        """
        # Only include stocks with BUY signals for optimization
        candidates = [
            a for a in analyses 
            if "BUY" in a.signal  # Must have BUY or STRONG_BUY signal
            and a.confidence >= self.min_confidence
            and "low" not in a.recommended_action.lower()
        ]
        
        if len(candidates) < 2:
            logger.warning("Not enough BUY candidates for optimization")
            # Fall back to equal weights for all buy signals
            if len(candidates) == 1:
                return {candidates[0].symbol: 1.0}
            return {}
        
        symbols = [a.symbol for a in candidates]
        
        # Get historical returns
        returns_data = {}
        for symbol in symbols:
            df = market_data.get_historical_data(symbol, period="1y")
            if df is not None:
                returns_data[symbol] = df['close'].pct_change().dropna()
        
        if len(returns_data) < 2:
            return {}
        
        returns_df = pd.DataFrame(returns_data).dropna()
        
        # Run optimization
        try:
            result = portfolio_optimizer.optimize_max_sharpe(returns_df)
            result.print_allocation()
            return result.weights
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return {}
    
    def execute_trades(self, analyses: List[StockAnalysis], weights: Dict[str, float] = None):
        """
        Execute trades based on analysis
        
        Args:
            analyses: List of stock analyses
            weights: Optional optimized weights
        """
        if self.dry_run:
            logger.info("🔒 DRY RUN - No trades will be executed")
            print("\n📋 SIMULATED TRADES:")
            print("-"*60)
        
        for analysis in analyses:
            if analysis.recommended_action == "HOLD" or "low confidence" in analysis.recommended_action:
                continue
            
            # Determine shares
            if weights and analysis.symbol in weights:
                # Use optimized weight
                allocation = self.portfolio_value * weights[analysis.symbol]
                shares = int(allocation / analysis.price)
            else:
                shares = analysis.position_size
            
            if shares <= 0:
                continue
            
            action = "BUY" if analysis.recommended_action == "BUY" else "SELL"
            
            if self.dry_run:
                print(f"  {action} {shares} shares of {analysis.symbol} @ ${analysis.price:.2f}")
                print(f"     Stop Loss: ${analysis.stop_loss:.2f} | Take Profit: ${analysis.take_profit:.2f}")
                print(f"     Reasons: {', '.join(analysis.reasons[:3])}")
            else:
                # Execute real trade
                try:
                    if action == "BUY":
                        order = alpaca_broker.buy(
                            symbol=analysis.symbol,
                            qty=shares,
                            order_type=OrderType.MARKET
                        )
                    else:
                        order = alpaca_broker.sell(
                            symbol=analysis.symbol,
                            qty=shares,
                            order_type=OrderType.MARKET
                        )
                    
                    logger.info(f"Order placed: {order}")
                    
                    # Send alert
                    notification_manager.trade_alert(
                        action=action,
                        symbol=analysis.symbol,
                        qty=shares,
                        price=analysis.price
                    )
                    
                except Exception as e:
                    logger.error(f"Trade execution failed: {e}")
                    notification_manager.error_alert(
                        error=f"Trade failed for {analysis.symbol}",
                        details=str(e)
                    )
        
        if self.dry_run:
            print("-"*60)
    
    def run_full_pipeline(self) -> Tuple[List[StockAnalysis], Dict[str, float]]:
        """
        Run the complete trading pipeline
        
        Returns:
            Tuple of (analyses, optimal_weights)
        """
        start_time = time.time()
        
        # Step 1: Scan and analyze
        analyses = self.run_scan()
        
        # Step 2: Portfolio optimization
        weights = self.optimize_portfolio(analyses)
        
        # Step 3: Execute trades
        self.execute_trades(analyses, weights)
        
        elapsed = time.time() - start_time
        logger.info(f"Pipeline completed in {elapsed:.1f} seconds")
        
        return analyses, weights
    
    def schedule_run(self, times: List[str] = None):
        """
        Schedule the pipeline to run at specific times
        
        Args:
            times: List of times in HH:MM format (default: market open/close)
        """
        if times is None:
            times = ["09:35", "12:00", "15:30"]  # After open, midday, before close
        
        for run_time in times:
            schedule.every().day.at(run_time).do(self.run_full_pipeline)
            logger.info(f"Scheduled run at {run_time}")
        
        logger.info("Starting scheduler... Press Ctrl+C to stop")
        
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    def _signal_to_score(self, signal) -> float:
        """Convert trading signal to numeric score"""
        # signal.signal is a SignalType enum, use .name for string or .value for int
        signal_map = {
            "STRONG_BUY": 1.0,
            "BUY": 0.5,
            "HOLD": 0.0,
            "SELL": -0.5,
            "STRONG_SELL": -1.0
        }
        # Use .name to get the string representation
        return signal_map.get(signal.signal.name, 0.0)
    
    def _score_to_signal(self, score: float) -> Tuple[str, float]:
        """Convert numeric score to signal and confidence"""
        abs_score = abs(score)
        confidence = min(abs_score * 2.5 + 0.3, 1.0)  # More generous confidence
        
        # Lowered thresholds for more actionable signals
        if score >= 0.25:
            return "STRONG_BUY", confidence
        elif score >= 0.10:
            return "BUY", confidence
        elif score <= -0.25:
            return "STRONG_SELL", confidence
        elif score <= -0.10:
            return "SELL", confidence
        else:
            return "HOLD", 0.5


def main():
    """Run the full trading pipeline"""
    
    # Default watchlist
    symbols = [
        # Tech
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
        # Finance
        "JPM", "BAC", "GS",
        # Healthcare  
        "JNJ", "UNH", "PFE",
        # ETFs
        "SPY", "QQQ", "IWM"
    ]
    
    # Initialize pipeline
    pipeline = TradingPipeline(
        symbols=symbols,
        portfolio_value=100000,
        max_position_pct=0.10,
        min_confidence=0.5,  # Lowered for more trades
        use_sentiment=True,
        use_deep_learning=False,  # Enable when models are trained
        dry_run=False,  # 🔴 LIVE TRADING ENABLED
        paper_trading=True  # ✅ Using PAPER account (safe)
    )
    
    # Run once
    analyses, weights = pipeline.run_full_pipeline()
    
    # Or schedule regular runs
    # pipeline.schedule_run(["09:35", "12:00", "15:30"])
    
    return analyses


if __name__ == "__main__":
    main()
