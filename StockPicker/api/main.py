"""
FastAPI Backend for StockPicker Dashboard
Provides REST API endpoints for the trading system
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
import traceback
import time
from loguru import logger

# Configure detailed logging
logger.remove()
logger.add(
    sys.stdout,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True
)
logger.add(
    "logs/api.log",
    rotation="10 MB",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from src.data import market_data, sentiment_analyzer, earnings_calendar
from src.features import indicators
from src.strategies import momentum_strategy
from src.risk import position_sizer, portfolio_optimizer
from src.broker import alpaca_broker, OrderType

app = FastAPI(
    title="StockPicker API",
    description="AI-powered stock trading system",
    version="1.0.0"
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log incoming request
    logger.info(f"📥 Incoming Request: {request.method} {request.url.path}")
    logger.debug(f"   Headers: {dict(request.headers)}")
    logger.debug(f"   Client: {request.client.host}:{request.client.port}")
    
    try:
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(f"📤 Response: {request.method} {request.url.path} - Status: {response.status_code} - Duration: {duration:.3f}s")
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"❌ Request Failed: {request.method} {request.url.path}")
        logger.error(f"   Error: {str(e)}")
        logger.error(f"   Duration: {duration:.3f}s")
        logger.error(f"   Traceback:\n{traceback.format_exc()}")
        raise

# CORS for Next.js frontend
# Configurable CORS (defaults to allow all in dev)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]
allow_credentials = False if origins == ["*"] else True

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("🚀 StockPicker API Starting...")

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("=" * 80)
    logger.info("🎯 StockPicker API Server Started Successfully!")
    logger.info("=" * 80)
    logger.info("📍 API Endpoints Available:")
    logger.info("   - GET  /                      - Root endpoint")
    logger.info("   - GET  /api/health            - Health check")
    logger.info("   - GET  /api/stocks            - Get stock list")
    logger.info("   - GET  /api/stock/{symbol}    - Get stock details")
    logger.info("   - GET  /api/stock/{symbol}/analysis - Get analysis")
    logger.info("   - POST /api/scan              - Run market scan")
    logger.info("   - POST /api/trade             - Execute trade")
    logger.info("   - GET  /api/portfolio         - Get portfolio")
    logger.info("   - GET  /docs                  - API Documentation")
    logger.info("=" * 80)
    logger.info("🌐 Server listening on: http://0.0.0.0:8000")
    logger.info("🔗 Frontend should connect to: http://localhost:8000")
    logger.info("=" * 80)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 StockPicker API Server Shutting Down...")

# ===== Models =====

class TradeRequest(BaseModel):
    symbol: str
    action: str  # "buy" or "sell"
    quantity: int
    order_type: str = "market"  # "market" or "limit"
    limit_price: Optional[float] = None

class ScanRequest(BaseModel):
    symbols: Optional[List[str]] = None
    
class BacktestRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float = 100000

# ===== Cache =====
scan_cache = {}
last_scan_time = None

# ===== Default Watchlist =====
DEFAULT_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "JPM", "BAC", "GS", "JNJ", "UNH", "PFE", "SPY", "QQQ", "IWM"
]

# ===== Endpoints =====

@app.get("/")
async def root():
    logger.debug("Root endpoint called")
    return {"message": "StockPicker API", "version": "1.0.0"}

@app.get("/api/health")
async def health_check():
    logger.debug("Health check endpoint called")
    result = {"status": "healthy", "timestamp": datetime.now().isoformat()}
    logger.debug(f"Health check result: {result}")
    return result

@app.get("/api/stocks")
async def get_stocks():
    """Get list of tracked stocks with current prices"""
    logger.info(f"📊 Fetching stock data for {len(DEFAULT_SYMBOLS)} symbols")
    stocks = []
    errors = []
    
    for symbol in DEFAULT_SYMBOLS:
        try:
            logger.debug(f"Fetching data for {symbol}")
            df = market_data.get_historical_data(symbol, period="5d")
            if df is not None and len(df) > 0:
                current = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else current
                change = ((current['close'] - prev['close']) / prev['close']) * 100
                stock_data = {
                    "symbol": symbol,
                    "price": round(current['close'], 2),
                    "change": round(change, 2),
                    "volume": int(current['volume']),
                    "high": round(current['high'], 2),
                    "low": round(current['low'], 2)
                }
                stocks.append(stock_data)
                logger.debug(f"✓ {symbol}: ${stock_data['price']} ({stock_data['change']:+.2f}%)")
        except Exception as e:
            error_msg = f"Error fetching {symbol}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.debug(f"Traceback for {symbol}:\n{traceback.format_exc()}")
            errors.append(error_msg)
    
    logger.info(f"✅ Successfully fetched {len(stocks)} stocks, {len(errors)} errors")
    return {"stocks": stocks}

@app.get("/api/stock/{symbol}")
async def get_stock_detail(symbol: str, period: str = "1y"):
    """Get detailed stock data with technical indicators"""
    logger.info(f"📈 Fetching detailed data for {symbol.upper()} (period: {period})")
    
    try:
        df = market_data.get_historical_data(symbol.upper(), period=period)
        if df is None:
            logger.warning(f"⚠️ Stock {symbol} not found or no data available")
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        logger.debug(f"Retrieved {len(df)} data points for {symbol}")
        logger.debug(f"Calculating technical indicators...")
        
        df = indicators.add_all_indicators(df)
        logger.debug(f"✓ Technical indicators calculated")
        
        # Convert to JSON-serializable format
        history = []
        for idx, row in df.iterrows():
            history.append({
                "date": idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                "open": round(row['open'], 2),
                "high": round(row['high'], 2),
                "low": round(row['low'], 2),
                "close": round(row['close'], 2),
                "volume": int(row['volume']),
                "sma_20": round(row.get('sma_20', 0), 2) if row.get('sma_20') else None,
                "sma_50": round(row.get('sma_50', 0), 2) if row.get('sma_50') else None,
                "rsi": round(row.get('rsi_14', 0), 2) if row.get('rsi_14') else None,
                "macd": round(row.get('macd', 0), 4) if row.get('macd') else None,
                "bb_upper": round(row.get('bb_upper', 0), 2) if row.get('bb_upper') else None,
                "bb_lower": round(row.get('bb_lower', 0), 2) if row.get('bb_lower') else None,
            })
        
        # Get latest values
        latest = df.iloc[-1]
        
        result = {
            "symbol": symbol.upper(),
            "history": history,
            "current": {
                "price": round(latest['close'], 2),
                "rsi": round(latest.get('rsi_14', 0), 2),
                "macd": round(latest.get('macd', 0), 4),
                "sma_20": round(latest.get('sma_20', 0), 2),
                "sma_50": round(latest.get('sma_50', 0), 2),
                "volume": int(latest['volume']),
                "atr": round(latest.get('atr_14', 0), 2),
            }
        }
        
        logger.info(f"✅ Successfully retrieved data for {symbol}: ${result['current']['price']}")
        logger.debug(f"Current indicators - RSI: {result['current']['rsi']}, MACD: {result['current']['macd']}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching stock detail for {symbol}: {str(e)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stock/{symbol}/analysis")
async def get_stock_analysis(symbol: str):
    """Get full analysis including signals and sentiment"""
    try:
        df = market_data.get_historical_data(symbol.upper(), period="1y")
        if df is None:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        df = indicators.add_all_indicators(df)
        
        # Technical analysis
        signal = momentum_strategy.analyze(df, symbol.upper())
        
        # Sentiment analysis
        try:
            sentiment = sentiment_analyzer.get_combined_sentiment(symbol.upper())
        except:
            sentiment = {"combined_sentiment": 0, "combined_label": "neutral"}
        
        # Earnings
        try:
            earnings = earnings_calendar.get_upcoming_earnings(symbol.upper())
        except:
            earnings = {"next_earnings_date": None}
        
        # Position sizing
        current_price = df.iloc[-1]['close']
        volatility = df['close'].pct_change().std() * (252 ** 0.5)
        shares, position_value = position_sizer.calculate_position_size(
            portfolio_value=100000,
            entry_price=current_price,
            volatility=volatility
        )
        
        # Calculate stop loss and take profit
        atr = df.iloc[-1].get('atr_14', current_price * 0.02)
        
        return {
            "symbol": symbol.upper(),
            "price": round(current_price, 2),
            "signal": {
                "type": signal.signal.name,
                "confidence": round(signal.confidence, 2),
                "reasons": signal.reasons
            },
            "sentiment": {
                "score": round(sentiment.get('combined_sentiment', 0), 2),
                "label": sentiment.get('combined_label', 'neutral')
            },
            "earnings": {
                "next_date": earnings.get('next_earnings_date'),
                "risk": earnings.get('earnings_risk', 'unknown')
            },
            "position": {
                "recommended_shares": shares,
                "position_value": round(position_value, 2),
                "stop_loss": round(current_price - (2 * atr), 2),
                "take_profit": round(current_price + (3 * atr), 2)
            },
            "indicators": {
                "rsi": round(df.iloc[-1].get('rsi_14', 0), 2),
                "macd": round(df.iloc[-1].get('macd', 0), 4),
                "adx": round(df.iloc[-1].get('adx_14', 0), 2),
                "bb_position": round(df.iloc[-1].get('bb_position', 0.5), 2)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scan")
async def run_market_scan(request: ScanRequest = None):
    """Run market scan on watchlist"""
    symbols = request.symbols if request and request.symbols else DEFAULT_SYMBOLS
    
    results = []
    for symbol in symbols:
        try:
            df = market_data.get_historical_data(symbol, period="1y")
            if df is None or len(df) < 50:
                continue
            
            df = indicators.add_all_indicators(df)
            signal = momentum_strategy.analyze(df, symbol)
            
            # Sentiment
            try:
                sentiment = sentiment_analyzer.get_combined_sentiment(symbol)
                sent_score = sentiment.get('combined_sentiment', 0)
            except:
                sent_score = 0
            
            # Calculate combined score
            tech_score = {"STRONG_BUY": 1, "BUY": 0.5, "HOLD": 0, "SELL": -0.5, "STRONG_SELL": -1}.get(signal.signal.name, 0)
            combined = (tech_score * 0.7) + (sent_score * 0.3)
            
            current = df.iloc[-1]
            prev = df.iloc[-2]
            change = ((current['close'] - prev['close']) / prev['close']) * 100
            
            results.append({
                "symbol": symbol,
                "price": round(current['close'], 2),
                "change": round(change, 2),
                "signal": signal.signal.name,
                "confidence": round(signal.confidence, 2),
                "technical_score": round(tech_score, 2),
                "sentiment_score": round(sent_score, 2),
                "combined_score": round(combined, 2),
                "rsi": round(current.get('rsi_14', 0), 2),
                "volume": int(current['volume']),
                "reasons": signal.reasons[:3]
            })
        except Exception as e:
            print(f"Scan error for {symbol}: {e}")
    
    # Sort by combined score
    results.sort(key=lambda x: x['combined_score'], reverse=True)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "count": len(results),
        "results": results
    }

@app.get("/api/hot-stocks")
async def get_hot_stocks():
    """Get top stocks by signal strength"""
    scan = await run_market_scan()
    
    buys = [r for r in scan['results'] if r['signal'] in ['STRONG_BUY', 'BUY']]
    sells = [r for r in scan['results'] if r['signal'] in ['STRONG_SELL', 'SELL']]
    
    return {
        "timestamp": scan['timestamp'],
        "top_buys": buys[:5],
        "top_sells": sells[:5],
        "all_signals": scan['results']
    }

@app.post("/api/trade")
async def execute_trade(trade: TradeRequest):
    """Execute a single trade"""
    try:
        symbol = trade.symbol.upper()
        
        if trade.action.lower() == "buy":
            order = alpaca_broker.buy(
                symbol=symbol,
                qty=trade.quantity,
                order_type=OrderType.MARKET if trade.order_type == "market" else OrderType.LIMIT,
                limit_price=trade.limit_price
            )
        elif trade.action.lower() == "sell":
            order = alpaca_broker.sell(
                symbol=symbol,
                qty=trade.quantity,
                order_type=OrderType.MARKET if trade.order_type == "market" else OrderType.LIMIT,
                limit_price=trade.limit_price
            )
        else:
            raise HTTPException(status_code=400, detail="Action must be 'buy' or 'sell'")
        
        return {
            "success": True,
            "order": {
                "id": str(order.id) if hasattr(order, 'id') else None,
                "symbol": symbol,
                "action": trade.action,
                "quantity": trade.quantity,
                "status": str(order.status) if hasattr(order, 'status') else "submitted"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/execute-pipeline")
async def execute_full_pipeline(background_tasks: BackgroundTasks):
    """Execute full trading pipeline"""
    try:
        # Run scan
        scan = await run_market_scan()
        
        # Filter actionable signals
        trades = []
        for stock in scan['results']:
            if stock['signal'] in ['STRONG_BUY', 'BUY'] and stock['confidence'] >= 0.5:
                # Calculate position size
                shares = min(int(10000 / stock['price']), 100)  # Max $10k or 100 shares
                trades.append({
                    "symbol": stock['symbol'],
                    "action": "buy",
                    "quantity": shares,
                    "price": stock['price'],
                    "signal": stock['signal'],
                    "confidence": stock['confidence']
                })
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "scan_results": len(scan['results']),
            "trades_to_execute": trades,
            "message": f"Found {len(trades)} actionable trades"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio")
async def get_portfolio():
    """Get current portfolio positions"""
    try:
        positions = alpaca_broker.get_positions()
        account = alpaca_broker.get_account()
        
        return {
            "account": {
                "buying_power": float(account.buying_power) if account else 0,
                "portfolio_value": float(account.portfolio_value) if account else 0,
                "cash": float(account.cash) if account else 0
            },
            "positions": [
                {
                    "symbol": p.symbol,
                    "qty": int(p.qty),
                    "avg_price": float(p.avg_entry_price),
                    "current_price": float(p.current_price),
                    "market_value": float(p.market_value),
                    "unrealized_pl": float(p.unrealized_pl),
                    "unrealized_plpc": float(p.unrealized_plpc) * 100
                }
                for p in (positions or [])
            ]
        }
    except Exception as e:
        return {
            "account": {"buying_power": 0, "portfolio_value": 0, "cash": 0},
            "positions": [],
            "error": str(e)
        }

@app.get("/api/orders")
async def get_orders(status: str = "all"):
    """Get recent orders"""
    try:
        orders = alpaca_broker.get_orders(status=status)
        return {
            "orders": [
                {
                    "id": str(o.id),
                    "symbol": o.symbol,
                    "side": o.side,
                    "qty": int(o.qty),
                    "type": o.type,
                    "status": o.status,
                    "created_at": str(o.created_at)
                }
                for o in (orders or [])
            ]
        }
    except Exception as e:
        return {"orders": [], "error": str(e)}

@app.delete("/api/orders/{order_id}")
async def cancel_order(order_id: str):
    """Cancel an order"""
    try:
        alpaca_broker.cancel_order(order_id)
        return {"success": True, "message": f"Order {order_id} cancelled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/optimize")
async def optimize_portfolio():
    """Run portfolio optimization"""
    try:
        import pandas as pd
        
        # Get returns for top stocks
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
        returns_data = {}
        
        for symbol in symbols:
            df = market_data.get_historical_data(symbol, period="1y")
            if df is not None:
                returns_data[symbol] = df['close'].pct_change().dropna()
        
        returns_df = pd.DataFrame(returns_data).dropna()
        
        result = portfolio_optimizer.optimize_max_sharpe(returns_df)
        
        return {
            "method": result.method,
            "expected_return": round(result.expected_return * 100, 2),
            "volatility": round(result.volatility * 100, 2),
            "sharpe_ratio": round(result.sharpe_ratio, 2),
            "weights": {k: round(v * 100, 1) for k, v in result.weights.items() if v > 0.01}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
