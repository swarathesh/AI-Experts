"""
Market Data Ingestion Module
Fetches historical and real-time stock data from various sources
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from loguru import logger
import time


class MarketDataFetcher:
    """Fetches and caches market data from multiple sources"""
    
    def __init__(self):
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_duration = timedelta(minutes=15)
    
    def get_historical_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1y",
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for a symbol
        
        Args:
            symbol: Stock ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        
        Returns:
            DataFrame with OHLCV data
        """
        cache_key = f"{symbol}_{start_date}_{end_date}_{period}_{interval}"
        
        # Check cache
        if self._is_cache_valid(cache_key):
            logger.debug(f"Returning cached data for {symbol}")
            return self._cache[cache_key]
        
        try:
            ticker = yf.Ticker(symbol)
            
            if start_date and end_date:
                df = ticker.history(start=start_date, end=end_date, interval=interval)
            else:
                df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()
            
            # Standardize column names
            df.columns = df.columns.str.lower()
            df.index.name = 'date'
            
            # Cache the result
            self._cache[cache_key] = df
            self._cache_expiry[cache_key] = datetime.now() + self._cache_duration
            
            logger.info(f"Fetched {len(df)} rows for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_multiple_stocks(
        self,
        symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1y"
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple symbols
        
        Args:
            symbols: List of ticker symbols
            start_date: Start date
            end_date: End date
            period: Time period
        
        Returns:
            Dictionary mapping symbols to DataFrames
        """
        data = {}
        
        for symbol in symbols:
            df = self.get_historical_data(
                symbol, 
                start_date=start_date, 
                end_date=end_date, 
                period=period
            )
            if not df.empty:
                data[symbol] = df
            time.sleep(0.1)  # Rate limiting
        
        return data
    
    def get_real_time_quote(self, symbol: str) -> Dict:
        """
        Get real-time quote for a symbol
        
        Args:
            symbol: Stock ticker symbol
        
        Returns:
            Dictionary with current price info
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                "symbol": symbol,
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "open": info.get("regularMarketOpen"),
                "high": info.get("dayHigh"),
                "low": info.get("dayLow"),
                "volume": info.get("volume"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "dividend_yield": info.get("dividendYield"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "avg_volume": info.get("averageVolume"),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            return {}
    
    def get_fundamentals(self, symbol: str) -> Dict:
        """
        Get fundamental data for a symbol
        
        Args:
            symbol: Stock ticker symbol
        
        Returns:
            Dictionary with fundamental metrics
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                "symbol": symbol,
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "enterprise_value": info.get("enterpriseValue"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "peg_ratio": info.get("pegRatio"),
                "price_to_book": info.get("priceToBook"),
                "price_to_sales": info.get("priceToSalesTrailing12Months"),
                "profit_margin": info.get("profitMargins"),
                "operating_margin": info.get("operatingMargins"),
                "roe": info.get("returnOnEquity"),
                "roa": info.get("returnOnAssets"),
                "revenue_growth": info.get("revenueGrowth"),
                "earnings_growth": info.get("earningsGrowth"),
                "debt_to_equity": info.get("debtToEquity"),
                "current_ratio": info.get("currentRatio"),
                "free_cash_flow": info.get("freeCashflow"),
                "beta": info.get("beta"),
            }
        except Exception as e:
            logger.error(f"Error getting fundamentals for {symbol}: {e}")
            return {}
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self._cache:
            return False
        if cache_key not in self._cache_expiry:
            return False
        return datetime.now() < self._cache_expiry[cache_key]
    
    def clear_cache(self):
        """Clear all cached data"""
        self._cache.clear()
        self._cache_expiry.clear()
        logger.info("Cache cleared")


# Singleton instance
market_data = MarketDataFetcher()
