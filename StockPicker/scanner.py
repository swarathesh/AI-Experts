"""
Market Scanner
Scans the market for trading opportunities based on technical criteria
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger
import sys

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")

from src.data import market_data
from src.features import indicators
from src.strategies import momentum_strategy, SignalType


# Expanded universe of stocks to scan
SCAN_UNIVERSE = [
    # Tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "INTC", "CRM",
    "ORCL", "ADBE", "NFLX", "PYPL", "SHOP", "SQ", "UBER", "ABNB", "SNOW", "PLTR",
    
    # Finance
    "JPM", "BAC", "WFC", "GS", "MS", "C", "AXP", "V", "MA", "BLK",
    
    # Healthcare
    "JNJ", "UNH", "PFE", "ABBV", "MRK", "TMO", "ABT", "LLY", "BMY", "AMGN",
    
    # Consumer
    "WMT", "PG", "KO", "PEP", "COST", "HD", "MCD", "NKE", "SBUX", "DIS",
    
    # Industrial
    "CAT", "BA", "GE", "MMM", "HON", "UPS", "RTX", "LMT", "DE", "UNP",
    
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "VLO", "PSX", "OXY", "HAL"
]


def scan_for_breakouts(data: Dict[str, pd.DataFrame], min_volume_ratio: float = 1.5) -> List[Dict]:
    """
    Scan for stocks breaking out of consolidation
    
    Criteria:
    - Price breaking above 20-day high
    - Volume > 1.5x average
    - RSI between 50-70 (momentum but not overbought)
    """
    breakouts = []
    
    for symbol, df in data.items():
        if len(df) < 20:
            continue
        
        latest = df.iloc[-1]
        high_20 = df['high'].rolling(20).max().iloc[-2]  # Previous 20-day high
        
        conditions = {
            "price_breakout": latest['close'] > high_20,
            "volume_surge": latest.get('volume_ratio', 0) > min_volume_ratio,
            "rsi_momentum": 50 < latest.get('rsi_14', 50) < 70,
            "above_sma50": latest['close'] > latest.get('sma_50', 0)
        }
        
        if all(conditions.values()):
            breakouts.append({
                "symbol": symbol,
                "pattern": "Breakout",
                "price": latest['close'],
                "volume_ratio": latest.get('volume_ratio', 0),
                "rsi": latest.get('rsi_14', 0),
                "score": sum(conditions.values()) / len(conditions)
            })
    
    return sorted(breakouts, key=lambda x: x['volume_ratio'], reverse=True)


def scan_for_oversold(data: Dict[str, pd.DataFrame]) -> List[Dict]:
    """
    Scan for oversold stocks with potential reversal
    
    Criteria:
    - RSI < 30
    - Price near lower Bollinger Band
    - Above 200-day SMA (long-term uptrend intact)
    """
    oversold = []
    
    for symbol, df in data.items():
        if len(df) < 200:
            continue
        
        latest = df.iloc[-1]
        
        conditions = {
            "rsi_oversold": latest.get('rsi_14', 50) < 30,
            "bb_oversold": latest.get('bb_position', 0.5) < 0.2,
            "uptrend_intact": latest['close'] > latest.get('sma_200', 0),
            "mfi_oversold": latest.get('mfi_14', 50) < 30
        }
        
        score = sum(conditions.values()) / len(conditions)
        
        if score >= 0.5:  # At least half the conditions met
            oversold.append({
                "symbol": symbol,
                "pattern": "Oversold Bounce",
                "price": latest['close'],
                "rsi": latest.get('rsi_14', 0),
                "bb_position": latest.get('bb_position', 0),
                "score": score
            })
    
    return sorted(oversold, key=lambda x: x['score'], reverse=True)


def scan_for_golden_cross(data: Dict[str, pd.DataFrame]) -> List[Dict]:
    """
    Scan for Golden Cross setups (50 SMA crossing above 200 SMA)
    """
    golden_crosses = []
    
    for symbol, df in data.items():
        if len(df) < 200:
            continue
        
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Golden cross just occurred
        cross_today = (latest.get('sma_50', 0) > latest.get('sma_200', 0) and 
                      previous.get('sma_50', 0) <= previous.get('sma_200', 0))
        
        # Or approaching golden cross
        approaching = (0.98 < latest.get('sma_50', 0) / latest.get('sma_200', 1) < 1.02 and
                      latest.get('sma_50', 0) > previous.get('sma_50', 0))
        
        if cross_today or approaching:
            golden_crosses.append({
                "symbol": symbol,
                "pattern": "Golden Cross" if cross_today else "Approaching Golden Cross",
                "price": latest['close'],
                "sma_50": latest.get('sma_50', 0),
                "sma_200": latest.get('sma_200', 0),
                "score": 1.0 if cross_today else 0.8
            })
    
    return sorted(golden_crosses, key=lambda x: x['score'], reverse=True)


def scan_for_macd_crossover(data: Dict[str, pd.DataFrame]) -> List[Dict]:
    """
    Scan for bullish MACD crossovers
    """
    crossovers = []
    
    for symbol, df in data.items():
        if len(df) < 30:
            continue
        
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        macd = latest.get('macd', 0)
        signal = latest.get('macd_signal', 0)
        prev_macd = previous.get('macd', 0)
        prev_signal = previous.get('macd_signal', 0)
        
        # Bullish crossover
        if macd > signal and prev_macd <= prev_signal:
            crossovers.append({
                "symbol": symbol,
                "pattern": "MACD Bullish Crossover",
                "price": latest['close'],
                "macd": macd,
                "macd_signal": signal,
                "histogram": latest.get('macd_histogram', 0),
                "score": 0.9 if macd > 0 else 0.7  # Higher score if above zero line
            })
    
    return sorted(crossovers, key=lambda x: x['score'], reverse=True)


def scan_for_high_momentum(data: Dict[str, pd.DataFrame], min_rsi: float = 60, max_rsi: float = 80) -> List[Dict]:
    """
    Scan for stocks with strong momentum
    
    Criteria:
    - RSI between 60-80 (strong momentum, not overbought)
    - Price above all major SMAs (20, 50, 200)
    - Positive MACD histogram
    - Volume above average
    """
    momentum_stocks = []
    
    for symbol, df in data.items():
        if len(df) < 200:
            continue
        
        latest = df.iloc[-1]
        
        rsi = latest.get('rsi_14', 50)
        sma_20 = latest.get('sma_20', 0)
        sma_50 = latest.get('sma_50', 0)
        sma_200 = latest.get('sma_200', 0)
        macd_hist = latest.get('macd_histogram', 0)
        volume_ratio = latest.get('volume_ratio', 1)
        
        conditions = {
            "strong_rsi": min_rsi < rsi < max_rsi,
            "above_sma20": latest['close'] > sma_20,
            "above_sma50": latest['close'] > sma_50,
            "above_sma200": latest['close'] > sma_200,
            "positive_macd": macd_hist > 0,
            "high_volume": volume_ratio > 1.2
        }
        
        score = sum(conditions.values()) / len(conditions)
        
        if score >= 0.7:  # At least 70% conditions met
            momentum_stocks.append({
                "symbol": symbol,
                "pattern": "High Momentum",
                "price": latest['close'],
                "rsi": rsi,
                "macd_histogram": macd_hist,
                "volume_ratio": volume_ratio,
                "score": score
            })
    
    return sorted(momentum_stocks, key=lambda x: x['score'], reverse=True)


def scan_market(symbols: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
    """
    Run all scans on the market
    
    Args:
        symbols: List of symbols to scan (uses default universe if not provided)
    
    Returns:
        Dictionary of scan results by pattern type
    """
    symbols = symbols or SCAN_UNIVERSE
    
    print("\n" + "="*60)
    print("  MARKET SCANNER")
    print(f"  Scanning {len(symbols)} stocks...")
    print("="*60)
    
    # Fetch data
    data = {}
    for symbol in symbols:
        try:
            df = market_data.get_historical_data(symbol, period="1y")
            if not df.empty and len(df) >= 50:
                df = indicators.add_all_indicators(df)
                data[symbol] = df.dropna()
        except Exception as e:
            logger.debug(f"Error fetching {symbol}: {e}")
    
    logger.info(f"Loaded data for {len(data)} symbols")
    
    # Run scans
    results = {
        "breakouts": scan_for_breakouts(data),
        "oversold": scan_for_oversold(data),
        "golden_cross": scan_for_golden_cross(data),
        "macd_crossover": scan_for_macd_crossover(data),
        "high_momentum": scan_for_high_momentum(data)
    }
    
    # Display results
    print("\n📈 BREAKOUT CANDIDATES:")
    print("-"*50)
    if results["breakouts"]:
        for stock in results["breakouts"][:5]:
            print(f"  {stock['symbol']:6} @ ${stock['price']:>8.2f}  |  Vol: {stock['volume_ratio']:.1f}x  RSI: {stock['rsi']:.0f}")
    else:
        print("  No breakouts detected")
    
    print("\n📉 OVERSOLD BOUNCE CANDIDATES:")
    print("-"*50)
    if results["oversold"]:
        for stock in results["oversold"][:5]:
            print(f"  {stock['symbol']:6} @ ${stock['price']:>8.2f}  |  RSI: {stock['rsi']:.0f}  BB: {stock['bb_position']:.2f}")
    else:
        print("  No oversold stocks detected")
    
    print("\n⭐ GOLDEN CROSS SETUPS:")
    print("-"*50)
    if results["golden_cross"]:
        for stock in results["golden_cross"][:5]:
            print(f"  {stock['symbol']:6} @ ${stock['price']:>8.2f}  |  {stock['pattern']}")
    else:
        print("  No golden cross setups")
    
    print("\n📊 MACD CROSSOVERS:")
    print("-"*50)
    if results["macd_crossover"]:
        for stock in results["macd_crossover"][:5]:
            print(f"  {stock['symbol']:6} @ ${stock['price']:>8.2f}  |  MACD: {stock['macd']:.2f}")
    else:
        print("  No MACD crossovers")
    
    # Top overall picks
    print("\n" + "="*60)
    print("🏆 TOP PICKS (HIGHEST CONVICTION):")
    print("="*60)
    
    # Combine and rank all signals
    all_picks = []
    for pattern_type, stocks in results.items():
        for stock in stocks[:3]:
            stock['pattern_type'] = pattern_type
            all_picks.append(stock)
    
    # Sort by score
    all_picks = sorted(all_picks, key=lambda x: x['score'], reverse=True)[:5]
    
    for i, pick in enumerate(all_picks, 1):
        print(f"\n  {i}. {pick['symbol']} @ ${pick['price']:.2f}")
        print(f"     Pattern: {pick['pattern']}")
        print(f"     Score: {pick['score']:.0%}")
    
    print("\n" + "="*60)
    print("⚠️  This is for educational purposes only. Not financial advice.")
    print("="*60 + "\n")
    
    return results


if __name__ == "__main__":
    scan_market()
