"""
Simplified FastAPI Backend - Minimal Version for Testing
This version has minimal dependencies to ensure it starts
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime
import traceback
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stdout, level="DEBUG", format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}", colorize=True)
logger.add("logs/api.log", rotation="10 MB", level="DEBUG")

app = FastAPI(title="StockPicker API", version="1.0.0")

# CORS (allow all in dev to support port-forwarded domains)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    logger.info("=" * 80)
    logger.info("🚀 StockPicker API Started!")
    logger.info("🌐 Listening on: http://0.0.0.0:8000")
    logger.info("=" * 80)

@app.get("/")
async def root():
    logger.debug("Root endpoint called")
    return {"message": "StockPicker API", "version": "1.0.0", "status": "running"}

@app.get("/api/health")
async def health_check():
    logger.debug("Health check called")
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/stocks")
async def get_stocks():
    logger.info("📊 Fetching stocks (mock data)")
    
    # Mock data for now
    mock_stocks = [
        {"symbol": "AAPL", "price": 185.50, "change": 2.34, "volume": 50000000, "high": 186.20, "low": 184.10},
        {"symbol": "MSFT", "price": 378.90, "change": 1.15, "volume": 30000000, "high": 380.50, "low": 376.80},
        {"symbol": "GOOGL", "price": 140.20, "change": -0.85, "volume": 25000000, "high": 141.50, "low": 139.80},
        {"symbol": "AMZN", "price": 151.30, "change": 3.20, "volume": 45000000, "high": 152.00, "low": 149.50},
        {"symbol": "NVDA", "price": 495.75, "change": 5.67, "volume": 60000000, "high": 498.20, "low": 492.10},
        {"symbol": "META", "price": 355.80, "change": 2.10, "volume": 28000000, "high": 357.50, "low": 353.20},
        {"symbol": "TSLA", "price": 238.45, "change": -1.45, "volume": 95000000, "high": 242.10, "low": 237.30},
        {"symbol": "JPM", "price": 158.20, "change": 0.75, "volume": 12000000, "high": 159.10, "low": 157.50},
    ]
    
    logger.info(f"✅ Returning {len(mock_stocks)} stocks")
    return {"stocks": mock_stocks}

@app.get("/api/hot-stocks")
async def get_hot_stocks():
    logger.info("🔥 Fetching hot stocks (mock data)")
    
    mock_data = {
        "top_buys": [
            {
                "symbol": "NVDA",
                "price": 495.75,
                "change": 5.67,
                "signal": "STRONG_BUY",
                "confidence": 0.92,
                "rsi": 65.5,
                "reasons": ["Strong momentum", "Golden cross", "High volume"]
            },
            {
                "symbol": "AAPL",
                "price": 185.50,
                "change": 2.34,
                "signal": "BUY",
                "confidence": 0.78,
                "rsi": 58.3,
                "reasons": ["Bullish MACD", "Above MA50", "Positive sentiment"]
            }
        ],
        "top_sells": [
            {
                "symbol": "GOOGL",
                "price": 140.20,
                "change": -0.85,
                "signal": "SELL",
                "confidence": 0.65,
                "rsi": 42.1,
                "reasons": ["Bearish divergence", "Below MA20"]
            }
        ]
    }
    
    logger.info(f"✅ Returning {len(mock_data['top_buys'])} buy signals, {len(mock_data['top_sells'])} sell signals")
    return mock_data

@app.get("/api/stock/{symbol}")
async def get_stock_detail(symbol: str, period: str = "1y"):
    logger.info(f"📈 Fetching {symbol} details (mock data)")
    
    # Mock historical data
    from datetime import timedelta
    base_date = datetime.now() - timedelta(days=30)
    
    history = []
    for i in range(30):
        date = base_date + timedelta(days=i)
        price = 150 + (i * 0.5)  # Simple uptrend
        history.append({
            "date": date.isoformat(),
            "open": round(price - 1, 2),
            "high": round(price + 2, 2),
            "low": round(price - 2, 2),
            "close": round(price, 2),
            "volume": 50000000 + (i * 100000),
            "sma_20": round(price - 0.5, 2),
            "sma_50": round(price - 1.5, 2),
            "rsi": 55 + (i % 10),
            "macd": 0.5 + (i * 0.01),
            "bb_upper": round(price + 3, 2),
            "bb_lower": round(price - 3, 2)
        })
    
    latest = history[-1]
    
    result = {
        "symbol": symbol.upper(),
        "history": history,
        "current": {
            "price": latest["close"],
            "rsi": latest["rsi"],
            "macd": latest["macd"],
            "sma_20": latest["sma_20"],
            "sma_50": latest["sma_50"],
            "volume": latest["volume"],
            "atr": 2.5
        }
    }
    
    logger.info(f"✅ Returning {len(history)} data points for {symbol}")
    return result

@app.get("/api/portfolio")
async def get_portfolio():
    logger.info("💼 Fetching portfolio (mock data)")
    
    mock_portfolio = {
        "total_value": 105000.00,
        "cash": 5000.00,
        "invested": 100000.00,
        "total_return": 5000.00,
        "total_return_pct": 5.0,
        "positions": [
            {"symbol": "AAPL", "quantity": 100, "avg_price": 180.00, "current_price": 185.50, "value": 18550.00, "pnl": 550.00, "pnl_pct": 3.06},
            {"symbol": "NVDA", "quantity": 50, "avg_price": 480.00, "current_price": 495.75, "value": 24787.50, "pnl": 787.50, "pnl_pct": 3.28},
            {"symbol": "MSFT", "quantity": 75, "avg_price": 370.00, "current_price": 378.90, "value": 28417.50, "pnl": 667.50, "pnl_pct": 2.41}
        ]
    }
    
    logger.info(f"✅ Portfolio value: ${mock_portfolio['total_value']:,.2f}")
    return mock_portfolio

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
