# StockPicker AI Agent 📈🤖

An intelligent stock market analysis and trading system that combines technical analysis, machine learning, sentiment analysis, and automated trade execution.

## Features ✅

### Data Layer
- **Market Data Ingestion**: Real-time and historical data from Yahoo Finance
- **News & Sentiment Analysis**: FinBERT + VADER for news/social media sentiment
- **Real-time Streaming**: WebSocket connection to Alpaca for live quotes
- **Earnings Calendar**: Track upcoming earnings and historical surprises

### Analysis Layer
- **Technical Analysis**: 50+ indicators (RSI, MACD, Bollinger Bands, ATR, VWAP, etc.)
- **ML Predictions**: Ensemble of XGBoost, LightGBM, and Random Forest
- **Deep Learning**: LSTM and Transformer models for time series prediction
- **Trading Strategies**: Momentum and Mean Reversion strategies

### Execution Layer
- **Alpaca Broker Integration**: Paper and live trading support
- **Portfolio Optimization**: Mean-Variance, Risk Parity, Black-Litterman
- **Risk Management**: Position sizing, Kelly criterion, stop-loss/take-profit
- **Market Scanner**: Automatic detection of setups and opportunities

### Alerting Layer
- **Email Notifications**: SMTP support (Gmail, etc.)
- **Slack Integration**: Webhook-based alerts
- **Discord Integration**: Rich embed notifications
- **Desktop Notifications**: Cross-platform alerts

## Project Structure

```
StockPicker/
├── config/
│   └── settings.py              # Configuration and parameters
├── src/
│   ├── data/
│   │   ├── market_data.py       # Yahoo Finance data fetching
│   │   ├── news_sentiment.py    # News & social sentiment analysis
│   │   └── realtime_stream.py   # WebSocket streaming
│   ├── features/
│   │   └── technical_indicators.py  # 50+ technical indicators
│   ├── models/
│   │   ├── ml_models.py         # XGBoost/LightGBM/RF ensemble
│   │   └── lstm_model.py        # LSTM & Transformer models
│   ├── strategies/
│   │   └── momentum.py          # Trading strategies
│   ├── backtest/
│   │   └── backtester.py        # Backtesting engine
│   ├── risk/
│   │   ├── portfolio.py         # Position sizing & risk metrics
│   │   └── portfolio_optimizer.py  # Mean-Variance optimization
│   ├── broker/
│   │   ├── alpaca_broker.py     # Alpaca API integration
│   │   └── order.py             # Order models
│   └── alerts/
│       └── notification_system.py  # Email/Slack/Discord alerts
├── main.py                      # Main entry point
├── scanner.py                   # Market scanner
├── trading_bot.py               # Automated trading bot
├── full_pipeline.py             # Complete end-to-end pipeline
├── quick_trade.py               # CLI for manual trades
├── requirements.txt
└── README.md
```

## Installation

1. **Clone and navigate to the project:**
```bash
cd StockPicker
```

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up API keys (optional):**
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Usage

### Quick Market Scan
```bash
python scanner.py
```
This scans 60+ stocks for:
- Breakout patterns
- Oversold bounce candidates
- Golden cross setups
- MACD crossovers

### Full Analysis with Backtest
```bash
python main.py
```
This runs:
1. Data fetching for watchlist stocks
2. Technical indicator calculation
3. Signal generation
4. Full backtest simulation
5. Performance metrics

### Use as a Library
```python
from src.data import market_data
from src.features import indicators
from src.strategies import momentum_strategy

# Fetch data
df = market_data.get_historical_data("AAPL", period="1y")

# Add indicators
df = indicators.add_all_indicators(df)

# Generate signal
signal = momentum_strategy.analyze(df, "AAPL")
print(f"Signal: {signal.signal.name}, Confidence: {signal.confidence:.1%}")
```

### Run Full End-to-End Pipeline
```bash
python full_pipeline.py
```
This runs the complete workflow:
1. Market data fetching
2. Technical analysis (50+ indicators)
3. ML predictions (ensemble)
4. Sentiment analysis (news + social)
5. Earnings risk check
6. Portfolio optimization
7. Trade execution (or dry run)
8. Alert notifications

### Start Automated Trading Bot
```bash
python trading_bot.py
```
Features:
- Scheduled scans (configurable intervals)
- Automatic trade execution
- Stop-loss and take-profit monitoring
- Dry-run mode for testing

### Unified Start (Backend + Dashboard)
To run the minimal backend with mock data and the dashboard together:

```bash
chmod +x start_all.sh
./start_all.sh --api-url http://localhost:8000 --mode minimal
```

In Codespaces or port-forwarded environments, use your forwarded 8000 URL:

```bash
./start_all.sh --api-url https://YOUR-FORWARDED-8000-URL.app.github.dev --mode minimal
```

This will:
- Start the backend on port 8000
- Set `StockPicker/dashboard/.env.local` with `NEXT_PUBLIC_API_URL`
- Start the dashboard on port 3001

### Quick Manual Trade
```bash
python quick_trade.py buy AAPL 10
python quick_trade.py sell MSFT 5
python quick_trade.py status
```

### Sentiment Analysis
```python
from src.data import sentiment_analyzer, earnings_calendar

# Get news sentiment
sentiment = sentiment_analyzer.get_combined_sentiment("AAPL")
print(f"Sentiment: {sentiment['combined_label']} ({sentiment['combined_sentiment']:.2f})")

# Check earnings
earnings = earnings_calendar.get_upcoming_earnings("AAPL")
print(f"Next earnings: {earnings['next_earnings_date']}")
```

### Portfolio Optimization
```python
from src.risk import portfolio_optimizer
import pandas as pd

# Get returns for multiple stocks
returns = pd.DataFrame({...})  # Historical returns

# Optimize for max Sharpe ratio
result = portfolio_optimizer.optimize_max_sharpe(returns)
result.print_allocation()
```

### Set Up Alerts
```python
from src.alerts import notification_manager, AlertPriority

# Configure channels (set env vars for API keys)
# Then send alerts:
notification_manager.price_alert("AAPL", 150.00, "above target")
notification_manager.signal_alert("NVDA", "STRONG_BUY", 0.85, 450.00)
```

## Trading Strategies

### 1. Momentum Strategy
Combines multiple indicators to identify trending stocks:
- **Trend Analysis**: Moving average crossovers, ADX
- **Momentum**: RSI, MACD, Stochastic
- **Volatility**: Bollinger Bands, ATR
- **Volume**: OBV, Volume ratio, MFI

### 2. Mean Reversion Strategy
Identifies oversold/overbought conditions:
- Z-score based deviation from mean
- Volume confirmation
- Support/resistance levels

### 3. ML Ensemble
Predicts price direction using:
- XGBoost (40% weight)
- LightGBM (35% weight)
- Random Forest (25% weight)

### 4. Deep Learning (LSTM/Transformer)
Advanced time series prediction:
- LSTM networks for sequence modeling
- Transformer with self-attention
- Hybrid ensemble combining all models

### 5. Sentiment-Driven
Incorporates market sentiment:
- FinBERT for financial text
- VADER for general sentiment
- News and Reddit sentiment aggregation

## Configuration

Edit `config/settings.py` to customize:

```python
# Risk parameters
max_position_size = 0.10  # 10% max per position
stop_loss_pct = 0.05      # 5% stop loss
take_profit_pct = 0.15    # 15% take profit

# Watchlist
watchlist = ["AAPL", "MSFT", "GOOGL", ...]

# Model settings
prediction_horizon = 5    # Days ahead to predict
min_confidence = 0.65     # Minimum signal confidence
```

## Backtest Results

The backtester provides:
- Total and annualized returns
- Sharpe and Sortino ratios
- Maximum drawdown
- Win rate and profit factor
- Trade statistics
- Equity curve

## ⚠️ Disclaimer

**This software is for educational purposes only.**

- Past performance does not guarantee future results
- Always do your own research before trading
- Never invest money you cannot afford to lose
- This is NOT financial advice

## Technical Indicators Included

| Category | Indicators |
|----------|------------|
| Trend | SMA (5,10,20,50,100,200), EMA (12,26,50), ADX |
| Momentum | RSI, MACD, Stochastic, Williams %R, ROC |
| Volatility | Bollinger Bands, ATR, Keltner Channels |
| Volume | OBV, VWAP, MFI, Volume Ratio |
| Price | Returns, Volatility, Gap, Candle patterns |

## Future Enhancements

- [ ] Options strategies integration
- [ ] Web dashboard with Streamlit
- [ ] Sector rotation strategy
- [ ] Crypto trading support

## License

MIT License - See LICENSE file for details.
