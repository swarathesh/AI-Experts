"""
Configuration settings for the StockPicker AI Agent
"""
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class APIConfig(BaseModel):
    """API configuration for data sources and brokers"""
    # Alpha Vantage (free tier: 5 calls/min)
    alpha_vantage_key: Optional[str] = os.getenv("ALPHA_VANTAGE_KEY")
    
    # Alpaca (paper trading)
    alpaca_api_key: Optional[str] = os.getenv("ALPACA_API_KEY")
    alpaca_secret_key: Optional[str] = os.getenv("ALPACA_SECRET_KEY")
    alpaca_base_url: str = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    
    # News API for sentiment
    news_api_key: Optional[str] = os.getenv("NEWS_API_KEY")


class TradingConfig(BaseModel):
    """Trading strategy configuration"""
    # Universe of stocks to scan
    watchlist: list[str] = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
        "JPM", "V", "JNJ", "WMT", "PG", "UNH", "HD", "MA"
    ]
    
    # Risk management
    max_position_size: float = 0.10  # Max 10% of portfolio per position
    max_portfolio_risk: float = 0.02  # Max 2% portfolio risk per trade
    stop_loss_pct: float = 0.05  # 5% stop loss
    take_profit_pct: float = 0.15  # 15% take profit
    
    # Trading parameters
    min_volume: int = 1_000_000  # Minimum daily volume
    min_price: float = 5.0  # Minimum stock price
    max_price: float = 1000.0  # Maximum stock price
    
    # Timing
    lookback_days: int = 252  # 1 year of trading days
    rebalance_frequency: str = "weekly"  # daily, weekly, monthly


class ModelConfig(BaseModel):
    """ML model configuration"""
    # Feature engineering
    technical_indicators: list[str] = [
        "sma_20", "sma_50", "sma_200",
        "ema_12", "ema_26",
        "rsi_14", "macd", "macd_signal",
        "bb_upper", "bb_lower", "bb_mid",
        "atr_14", "obv", "vwap"
    ]
    
    # Model parameters
    prediction_horizon: int = 5  # Predict 5 days ahead
    train_test_split: float = 0.8
    validation_split: float = 0.1
    
    # Ensemble weights
    model_weights: dict = {
        "xgboost": 0.4,
        "lightgbm": 0.3,
        "random_forest": 0.3
    }
    
    # Confidence threshold for trading signals
    min_confidence: float = 0.65


class BacktestConfig(BaseModel):
    """Backtesting configuration"""
    initial_capital: float = 100_000.0
    commission: float = 0.001  # 0.1% per trade
    slippage: float = 0.001  # 0.1% slippage
    start_date: str = "2020-01-01"
    end_date: str = "2024-12-31"


class Settings(BaseModel):
    """Main settings container"""
    api: APIConfig = APIConfig()
    trading: TradingConfig = TradingConfig()
    model: ModelConfig = ModelConfig()
    backtest: BacktestConfig = BacktestConfig()
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/stockpicker.log"


# Global settings instance
settings = Settings()
