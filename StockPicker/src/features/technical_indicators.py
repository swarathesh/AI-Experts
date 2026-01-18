"""
Technical Indicators Module
Calculates various technical indicators for trading signals
"""
import pandas as pd
import numpy as np
from typing import Optional
from loguru import logger


class TechnicalIndicators:
    """Calculate technical indicators for stock data"""
    
    @staticmethod
    def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add all technical indicators to a DataFrame
        
        Args:
            df: DataFrame with OHLCV data (columns: open, high, low, close, volume)
        
        Returns:
            DataFrame with added indicator columns
        """
        df = df.copy()
        
        # Trend Indicators
        df = TechnicalIndicators.add_moving_averages(df)
        df = TechnicalIndicators.add_macd(df)
        df = TechnicalIndicators.add_adx(df)
        
        # Momentum Indicators
        df = TechnicalIndicators.add_rsi(df)
        df = TechnicalIndicators.add_stochastic(df)
        df = TechnicalIndicators.add_williams_r(df)
        df = TechnicalIndicators.add_momentum(df)
        
        # Volatility Indicators
        df = TechnicalIndicators.add_bollinger_bands(df)
        df = TechnicalIndicators.add_atr(df)
        df = TechnicalIndicators.add_keltner_channels(df)
        
        # Volume Indicators
        df = TechnicalIndicators.add_obv(df)
        df = TechnicalIndicators.add_vwap(df)
        df = TechnicalIndicators.add_mfi(df)
        
        # Price Features
        df = TechnicalIndicators.add_price_features(df)
        
        return df
    
    @staticmethod
    def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
        """Add Simple and Exponential Moving Averages"""
        df = df.copy()
        
        # Simple Moving Averages
        for period in [5, 10, 20, 50, 100, 200]:
            df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
        
        # Exponential Moving Averages
        for period in [12, 26, 50]:
            df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        
        # Moving Average Crossover Signals
        df['sma_cross_20_50'] = (df['sma_20'] > df['sma_50']).astype(int)
        df['sma_cross_50_200'] = (df['sma_50'] > df['sma_200']).astype(int)
        
        # Price relative to MAs
        df['price_to_sma_20'] = df['close'] / df['sma_20']
        df['price_to_sma_50'] = df['close'] / df['sma_50']
        df['price_to_sma_200'] = df['close'] / df['sma_200']
        
        return df
    
    @staticmethod
    def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """Add MACD indicator"""
        df = df.copy()
        
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # MACD crossover signal
        df['macd_cross'] = (df['macd'] > df['macd_signal']).astype(int)
        
        return df
    
    @staticmethod
    def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Add Relative Strength Index"""
        df = df.copy()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
        
        # RSI zones
        df['rsi_oversold'] = (df[f'rsi_{period}'] < 30).astype(int)
        df['rsi_overbought'] = (df[f'rsi_{period}'] > 70).astype(int)
        
        return df
    
    @staticmethod
    def add_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
        """Add Stochastic Oscillator"""
        df = df.copy()
        
        low_min = df['low'].rolling(window=k_period).min()
        high_max = df['high'].rolling(window=k_period).max()
        
        df['stoch_k'] = 100 * (df['close'] - low_min) / (high_max - low_min)
        df['stoch_d'] = df['stoch_k'].rolling(window=d_period).mean()
        
        return df
    
    @staticmethod
    def add_williams_r(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Add Williams %R"""
        df = df.copy()
        
        high_max = df['high'].rolling(window=period).max()
        low_min = df['low'].rolling(window=period).min()
        
        df['williams_r'] = -100 * (high_max - df['close']) / (high_max - low_min)
        
        return df
    
    @staticmethod
    def add_momentum(df: pd.DataFrame, period: int = 10) -> pd.DataFrame:
        """Add Momentum indicator"""
        df = df.copy()
        
        df[f'momentum_{period}'] = df['close'] - df['close'].shift(period)
        df[f'roc_{period}'] = (df['close'] / df['close'].shift(period) - 1) * 100
        
        return df
    
    @staticmethod
    def add_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
        """Add Bollinger Bands"""
        df = df.copy()
        
        df['bb_mid'] = df['close'].rolling(window=period).mean()
        rolling_std = df['close'].rolling(window=period).std()
        
        df['bb_upper'] = df['bb_mid'] + (rolling_std * std_dev)
        df['bb_lower'] = df['bb_mid'] - (rolling_std * std_dev)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        return df
    
    @staticmethod
    def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Add Average True Range"""
        df = df.copy()
        
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df[f'atr_{period}'] = true_range.rolling(window=period).mean()
        
        # ATR percentage
        df['atr_pct'] = df[f'atr_{period}'] / df['close'] * 100
        
        return df
    
    @staticmethod
    def add_keltner_channels(df: pd.DataFrame, period: int = 20, atr_mult: float = 2.0) -> pd.DataFrame:
        """Add Keltner Channels"""
        df = df.copy()
        
        # Need ATR first
        if f'atr_{period}' not in df.columns:
            df = TechnicalIndicators.add_atr(df, period)
        
        ema = df['close'].ewm(span=period, adjust=False).mean()
        df['keltner_mid'] = ema
        df['keltner_upper'] = ema + (atr_mult * df[f'atr_{period}'])
        df['keltner_lower'] = ema - (atr_mult * df[f'atr_{period}'])
        
        return df
    
    @staticmethod
    def add_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Add Average Directional Index"""
        df = df.copy()
        
        # Calculate +DM and -DM
        df['up_move'] = df['high'] - df['high'].shift(1)
        df['down_move'] = df['low'].shift(1) - df['low']
        
        df['+dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
        df['-dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)
        
        # Need ATR
        if f'atr_{period}' not in df.columns:
            df = TechnicalIndicators.add_atr(df, period)
        
        # Calculate +DI and -DI
        df['+di'] = 100 * (df['+dm'].ewm(span=period, adjust=False).mean() / df[f'atr_{period}'])
        df['-di'] = 100 * (df['-dm'].ewm(span=period, adjust=False).mean() / df[f'atr_{period}'])
        
        # Calculate DX and ADX
        df['dx'] = 100 * abs(df['+di'] - df['-di']) / (df['+di'] + df['-di'])
        df[f'adx_{period}'] = df['dx'].ewm(span=period, adjust=False).mean()
        
        # Cleanup intermediate columns
        df.drop(['up_move', 'down_move', '+dm', '-dm', 'dx'], axis=1, inplace=True)
        
        return df
    
    @staticmethod
    def add_obv(df: pd.DataFrame) -> pd.DataFrame:
        """Add On-Balance Volume"""
        df = df.copy()
        
        obv = [0]
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.append(obv[-1] + df['volume'].iloc[i])
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.append(obv[-1] - df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        
        df['obv'] = obv
        df['obv_sma'] = df['obv'].rolling(window=20).mean()
        
        return df
    
    @staticmethod
    def add_vwap(df: pd.DataFrame) -> pd.DataFrame:
        """Add Volume Weighted Average Price"""
        df = df.copy()
        
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        df['price_to_vwap'] = df['close'] / df['vwap']
        
        return df
    
    @staticmethod
    def add_mfi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Add Money Flow Index"""
        df = df.copy()
        
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        raw_money_flow = typical_price * df['volume']
        
        positive_flow = []
        negative_flow = []
        
        for i in range(1, len(df)):
            if typical_price.iloc[i] > typical_price.iloc[i-1]:
                positive_flow.append(raw_money_flow.iloc[i])
                negative_flow.append(0)
            else:
                positive_flow.append(0)
                negative_flow.append(raw_money_flow.iloc[i])
        
        positive_flow = [0] + positive_flow
        negative_flow = [0] + negative_flow
        
        positive_mf = pd.Series(positive_flow).rolling(window=period).sum()
        negative_mf = pd.Series(negative_flow).rolling(window=period).sum()
        
        mfi = 100 - (100 / (1 + positive_mf / negative_mf))
        df[f'mfi_{period}'] = mfi.values
        
        return df
    
    @staticmethod
    def add_price_features(df: pd.DataFrame) -> pd.DataFrame:
        """Add price-based features"""
        df = df.copy()
        
        # Returns
        df['return_1d'] = df['close'].pct_change(1)
        df['return_5d'] = df['close'].pct_change(5)
        df['return_10d'] = df['close'].pct_change(10)
        df['return_20d'] = df['close'].pct_change(20)
        
        # Volatility
        df['volatility_10d'] = df['return_1d'].rolling(window=10).std() * np.sqrt(252)
        df['volatility_20d'] = df['return_1d'].rolling(window=20).std() * np.sqrt(252)
        
        # Price gaps
        df['gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
        
        # Candle patterns
        df['body'] = df['close'] - df['open']
        df['upper_shadow'] = df['high'] - df[['close', 'open']].max(axis=1)
        df['lower_shadow'] = df[['close', 'open']].min(axis=1) - df['low']
        df['body_to_range'] = df['body'].abs() / (df['high'] - df['low'])
        
        # High/Low position
        df['hl_range'] = df['high'] - df['low']
        df['close_position'] = (df['close'] - df['low']) / df['hl_range']
        
        # Volume features
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']
        
        return df


# Create instance
indicators = TechnicalIndicators()
