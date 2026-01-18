"""
Momentum Trading Strategy
Implements a momentum-based trading strategy with multiple signals
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from loguru import logger
from dataclasses import dataclass
from enum import Enum


class SignalType(Enum):
    STRONG_BUY = 2
    BUY = 1
    HOLD = 0
    SELL = -1
    STRONG_SELL = -2


@dataclass
class TradingSignal:
    """Represents a trading signal"""
    symbol: str
    signal: SignalType
    confidence: float
    price: float
    reasons: List[str]
    timestamp: str
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "signal": self.signal.name,
            "signal_value": self.signal.value,
            "confidence": self.confidence,
            "price": self.price,
            "reasons": self.reasons,
            "timestamp": self.timestamp
        }


class MomentumStrategy:
    """
    Momentum-based trading strategy
    
    Combines multiple technical indicators to generate trading signals:
    - Trend following (moving average crossovers)
    - Momentum (RSI, MACD)
    - Volatility (Bollinger Bands)
    - Volume confirmation
    """
    
    def __init__(
        self,
        rsi_oversold: float = 30,
        rsi_overbought: float = 70,
        bb_oversold: float = 0.2,
        bb_overbought: float = 0.8,
        volume_threshold: float = 1.5
    ):
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.bb_oversold = bb_oversold
        self.bb_overbought = bb_overbought
        self.volume_threshold = volume_threshold
    
    def analyze(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> TradingSignal:
        """
        Analyze a stock and generate a trading signal
        
        Args:
            df: DataFrame with technical indicators
            symbol: Stock symbol
        
        Returns:
            TradingSignal with recommendation
        """
        if len(df) < 2:
            return TradingSignal(
                symbol=symbol,
                signal=SignalType.HOLD,
                confidence=0.0,
                price=0.0,
                reasons=["Insufficient data"],
                timestamp=str(pd.Timestamp.now())
            )
        
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        bullish_signals = []
        bearish_signals = []
        
        # 1. Trend Analysis (Moving Averages)
        trend_score = self._analyze_trend(latest, bullish_signals, bearish_signals)
        
        # 2. Momentum Analysis (RSI, MACD)
        momentum_score = self._analyze_momentum(latest, previous, bullish_signals, bearish_signals)
        
        # 3. Volatility Analysis (Bollinger Bands)
        volatility_score = self._analyze_volatility(latest, bullish_signals, bearish_signals)
        
        # 4. Volume Confirmation
        volume_score = self._analyze_volume(latest, bullish_signals, bearish_signals)
        
        # Calculate overall score
        weights = {"trend": 0.3, "momentum": 0.35, "volatility": 0.2, "volume": 0.15}
        total_score = (
            weights["trend"] * trend_score +
            weights["momentum"] * momentum_score +
            weights["volatility"] * volatility_score +
            weights["volume"] * volume_score
        )
        
        # Determine signal
        signal, confidence = self._determine_signal(total_score, bullish_signals, bearish_signals)
        
        reasons = bullish_signals + bearish_signals if bullish_signals or bearish_signals else ["No clear signals"]
        
        return TradingSignal(
            symbol=symbol,
            signal=signal,
            confidence=confidence,
            price=latest['close'] if 'close' in latest else 0.0,
            reasons=reasons,
            timestamp=str(latest.name if hasattr(latest, 'name') else pd.Timestamp.now())
        )
    
    def _analyze_trend(self, latest: pd.Series, bullish: List, bearish: List) -> float:
        """Analyze trend indicators"""
        score = 0
        
        # Price above/below key moving averages
        if 'price_to_sma_20' in latest:
            if latest['price_to_sma_20'] > 1.02:
                score += 1
                bullish.append("Price above SMA20")
            elif latest['price_to_sma_20'] < 0.98:
                score -= 1
                bearish.append("Price below SMA20")
        
        if 'price_to_sma_50' in latest:
            if latest['price_to_sma_50'] > 1.02:
                score += 1
                bullish.append("Price above SMA50")
            elif latest['price_to_sma_50'] < 0.98:
                score -= 1
                bearish.append("Price below SMA50")
        
        # Golden/Death cross
        if 'sma_cross_50_200' in latest:
            if latest['sma_cross_50_200'] == 1:
                score += 1.5
                bullish.append("Golden cross (SMA50 > SMA200)")
            else:
                score -= 1.5
                bearish.append("Death cross (SMA50 < SMA200)")
        
        # ADX trend strength
        if 'adx_14' in latest:
            if latest['adx_14'] > 25:
                # Strong trend - add to existing direction
                if score > 0:
                    score += 0.5
                    bullish.append(f"Strong trend (ADX: {latest['adx_14']:.1f})")
                elif score < 0:
                    score -= 0.5
                    bearish.append(f"Strong trend (ADX: {latest['adx_14']:.1f})")
        
        # Normalize to [-1, 1]
        return np.clip(score / 4, -1, 1)
    
    def _analyze_momentum(self, latest: pd.Series, previous: pd.Series, bullish: List, bearish: List) -> float:
        """Analyze momentum indicators"""
        score = 0
        
        # RSI
        if 'rsi_14' in latest:
            rsi = latest['rsi_14']
            if rsi < 20:  # Extremely oversold
                score += 2.5
                bullish.append(f"RSI extremely oversold ({rsi:.1f})")
            elif rsi < self.rsi_oversold:
                score += 1.5
                bullish.append(f"RSI oversold ({rsi:.1f})")
            elif rsi > 80:  # Extremely overbought
                score -= 2.5
                bearish.append(f"RSI extremely overbought ({rsi:.1f})")
            elif rsi > self.rsi_overbought:
                score -= 1.5
                bearish.append(f"RSI overbought ({rsi:.1f})")
            elif rsi > 50:
                score += 0.3
            else:
                score -= 0.3
        
        # MACD
        if 'macd' in latest and 'macd_signal' in latest:
            macd = latest['macd']
            signal = latest['macd_signal']
            prev_macd = previous.get('macd', macd)
            prev_signal = previous.get('macd_signal', signal)
            
            # MACD crossover
            if macd > signal and prev_macd <= prev_signal:
                score += 1.5
                bullish.append("MACD bullish crossover")
            elif macd < signal and prev_macd >= prev_signal:
                score -= 1.5
                bearish.append("MACD bearish crossover")
            
            # MACD histogram
            if 'macd_histogram' in latest:
                hist = latest['macd_histogram']
                prev_hist = previous.get('macd_histogram', hist)
                if hist > 0 and hist > prev_hist:
                    score += 0.5
                    bullish.append("MACD histogram increasing")
                elif hist < 0 and hist < prev_hist:
                    score -= 0.5
                    bearish.append("MACD histogram decreasing")
        
        # Stochastic
        if 'stoch_k' in latest and 'stoch_d' in latest:
            k = latest['stoch_k']
            d = latest['stoch_d']
            if k < 20 and k > d:
                score += 1
                bullish.append("Stochastic oversold crossover")
            elif k > 80 and k < d:
                score -= 1
                bearish.append("Stochastic overbought crossover")
        
        return np.clip(score / 4.5, -1, 1)
    
    def _analyze_volatility(self, latest: pd.Series, bullish: List, bearish: List) -> float:
        """Analyze volatility indicators"""
        score = 0
        
        # Bollinger Band position
        if 'bb_position' in latest:
            bb_pos = latest['bb_position']
            if bb_pos < self.bb_oversold:
                score += 1.5
                bullish.append(f"Near lower Bollinger Band ({bb_pos:.2f})")
            elif bb_pos > self.bb_overbought:
                score -= 1.5
                bearish.append(f"Near upper Bollinger Band ({bb_pos:.2f})")
        
        # Bollinger Band squeeze (low volatility before breakout)
        if 'bb_width' in latest:
            if latest['bb_width'] < 0.1:
                bullish.append("Bollinger squeeze - potential breakout")
        
        # ATR for position sizing (informational)
        if 'atr_pct' in latest:
            atr_pct = latest['atr_pct']
            if atr_pct > 5:
                bearish.append(f"High volatility (ATR: {atr_pct:.1f}%)")
        
        return np.clip(score / 1.5, -1, 1)
    
    def _analyze_volume(self, latest: pd.Series, bullish: List, bearish: List) -> float:
        """Analyze volume indicators"""
        score = 0
        
        # Volume ratio
        if 'volume_ratio' in latest:
            vol_ratio = latest['volume_ratio']
            if vol_ratio > self.volume_threshold:
                if 'return_1d' in latest:
                    if latest['return_1d'] > 0:
                        score += 1
                        bullish.append(f"High volume up day ({vol_ratio:.1f}x avg)")
                    else:
                        score -= 1
                        bearish.append(f"High volume down day ({vol_ratio:.1f}x avg)")
        
        # OBV trend
        if 'obv' in latest and 'obv_sma' in latest:
            if latest['obv'] > latest['obv_sma']:
                score += 0.5
                bullish.append("OBV above average")
            else:
                score -= 0.5
                bearish.append("OBV below average")
        
        # MFI
        if 'mfi_14' in latest:
            mfi = latest['mfi_14']
            if mfi < 20:
                score += 1
                bullish.append(f"MFI oversold ({mfi:.1f})")
            elif mfi > 80:
                score -= 1
                bearish.append(f"MFI overbought ({mfi:.1f})")
        
        return np.clip(score / 2.5, -1, 1)
    
    def _determine_signal(
        self, 
        score: float, 
        bullish: List, 
        bearish: List
    ) -> Tuple[SignalType, float]:
        """Determine final signal from score"""
        
        # Count signals for confidence
        total_signals = len(bullish) + len(bearish)
        agreement = abs(len(bullish) - len(bearish)) / max(total_signals, 1)
        
        confidence = min(abs(score) * 0.6 + agreement * 0.4, 1.0)
        
        # Lowered thresholds for more actionable signals
        if score > 0.4:
            return SignalType.STRONG_BUY, confidence
        elif score > 0.15:
            return SignalType.BUY, confidence
        elif score < -0.4:
            return SignalType.STRONG_SELL, confidence
        elif score < -0.15:
            return SignalType.SELL, confidence
        else:
            return SignalType.HOLD, confidence


class MeanReversionStrategy:
    """
    Mean Reversion Strategy
    
    Identifies stocks that have deviated significantly from their mean
    and are likely to revert back.
    """
    
    def __init__(
        self,
        zscore_threshold: float = 2.0,
        lookback_period: int = 20,
        min_volume_ratio: float = 1.0
    ):
        self.zscore_threshold = zscore_threshold
        self.lookback_period = lookback_period
        self.min_volume_ratio = min_volume_ratio
    
    def analyze(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> TradingSignal:
        """
        Analyze for mean reversion opportunities
        
        Args:
            df: DataFrame with price data
            symbol: Stock symbol
        
        Returns:
            TradingSignal
        """
        if len(df) < self.lookback_period:
            return TradingSignal(
                symbol=symbol,
                signal=SignalType.HOLD,
                confidence=0.0,
                price=0.0,
                reasons=["Insufficient data for mean reversion"],
                timestamp=str(pd.Timestamp.now())
            )
        
        latest = df.iloc[-1]
        reasons = []
        
        # Calculate z-score of current price
        mean_price = df['close'].rolling(self.lookback_period).mean().iloc[-1]
        std_price = df['close'].rolling(self.lookback_period).std().iloc[-1]
        
        if std_price == 0:
            zscore = 0
        else:
            zscore = (latest['close'] - mean_price) / std_price
        
        # Check volume confirmation
        volume_ok = True
        if 'volume_ratio' in latest:
            volume_ok = latest['volume_ratio'] >= self.min_volume_ratio
        
        # Determine signal
        if zscore < -self.zscore_threshold and volume_ok:
            signal = SignalType.BUY
            confidence = min(abs(zscore) / 3, 1.0)
            reasons.append(f"Price {abs(zscore):.1f} std below mean - oversold")
        elif zscore > self.zscore_threshold and volume_ok:
            signal = SignalType.SELL
            confidence = min(abs(zscore) / 3, 1.0)
            reasons.append(f"Price {abs(zscore):.1f} std above mean - overbought")
        else:
            signal = SignalType.HOLD
            confidence = 0.3
            reasons.append(f"Z-score: {zscore:.2f} - within normal range")
        
        return TradingSignal(
            symbol=symbol,
            signal=signal,
            confidence=confidence,
            price=latest['close'],
            reasons=reasons,
            timestamp=str(latest.name if hasattr(latest, 'name') else pd.Timestamp.now())
        )


# Strategy instances
momentum_strategy = MomentumStrategy()
mean_reversion_strategy = MeanReversionStrategy()
