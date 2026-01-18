"""
StockPicker AI Agent
An intelligent stock market analysis and trading system
"""
from .data import MarketDataFetcher, market_data, NewsSentimentAnalyzer, sentiment_analyzer, EarningsCalendar, earnings_calendar, RealtimeMonitor, realtime_monitor
from .features import TechnicalIndicators, indicators
from .models import StockPredictor, SignalGenerator, predictor, LSTMPredictor, lstm_predictor, HybridEnsemble, hybrid_ensemble
from .strategies import MomentumStrategy, MeanReversionStrategy, momentum_strategy, mean_reversion_strategy
from .backtest import Backtester, BacktestResult, backtester
from .risk import PortfolioManager, PositionSizer, portfolio_manager, position_sizer, PortfolioOptimizer, portfolio_optimizer
from .broker import AlpacaBroker, alpaca_broker, Order, OrderSide, OrderType
from .alerts import NotificationManager, notification_manager, Alert, AlertType, AlertPriority, send_alert

__version__ = "0.2.0"
__all__ = [
    # Data
    "MarketDataFetcher", "market_data",
    "NewsSentimentAnalyzer", "sentiment_analyzer",
    "EarningsCalendar", "earnings_calendar",
    "RealtimeMonitor", "realtime_monitor",
    # Features
    "TechnicalIndicators", "indicators",
    # Models
    "StockPredictor", "SignalGenerator", "predictor",
    "LSTMPredictor", "lstm_predictor", "HybridEnsemble", "hybrid_ensemble",
    # Strategies
    "MomentumStrategy", "MeanReversionStrategy", "momentum_strategy", "mean_reversion_strategy",
    # Backtesting
    "Backtester", "BacktestResult", "backtester",
    # Risk Management
    "PortfolioManager", "PositionSizer", "portfolio_manager", "position_sizer",
    "PortfolioOptimizer", "portfolio_optimizer",
    # Broker
    "AlpacaBroker", "alpaca_broker", "Order", "OrderSide", "OrderType",
    # Alerts
    "NotificationManager", "notification_manager", "Alert", "AlertType", "AlertPriority", "send_alert"
]
