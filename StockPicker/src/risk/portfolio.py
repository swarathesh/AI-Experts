"""
Portfolio & Risk Management Module
Handles position sizing, risk allocation, and portfolio optimization
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class Position:
    """Represents a portfolio position"""
    symbol: str
    shares: int
    entry_price: float
    current_price: float
    weight: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    
    @property
    def market_value(self) -> float:
        return self.shares * self.current_price


@dataclass
class RiskMetrics:
    """Portfolio risk metrics"""
    portfolio_value: float
    cash: float
    invested: float
    num_positions: int
    portfolio_beta: float
    portfolio_volatility: float
    var_95: float  # Value at Risk (95%)
    max_position_weight: float
    concentration_risk: float  # Herfindahl index
    
    def to_dict(self) -> Dict:
        return {
            "portfolio_value": f"${self.portfolio_value:,.2f}",
            "cash": f"${self.cash:,.2f}",
            "invested": f"${self.invested:,.2f}",
            "num_positions": self.num_positions,
            "portfolio_beta": f"{self.portfolio_beta:.2f}",
            "portfolio_volatility": f"{self.portfolio_volatility:.2%}",
            "var_95": f"${self.var_95:,.2f}",
            "max_position_weight": f"{self.max_position_weight:.2%}",
            "concentration_risk": f"{self.concentration_risk:.2f}"
        }


class PositionSizer:
    """
    Calculates optimal position sizes based on risk parameters
    """
    
    def __init__(
        self,
        max_position_pct: float = 0.10,
        max_portfolio_risk: float = 0.02,
        default_stop_loss: float = 0.05
    ):
        """
        Initialize position sizer
        
        Args:
            max_position_pct: Maximum position size as fraction of portfolio
            max_portfolio_risk: Maximum risk per trade as fraction of portfolio
            default_stop_loss: Default stop loss percentage
        """
        self.max_position_pct = max_position_pct
        self.max_portfolio_risk = max_portfolio_risk
        self.default_stop_loss = default_stop_loss
    
    def calculate_position_size(
        self,
        portfolio_value: float,
        entry_price: float,
        stop_loss_pct: Optional[float] = None,
        volatility: Optional[float] = None
    ) -> Tuple[int, float]:
        """
        Calculate optimal position size
        
        Uses the fixed fractional / Kelly-inspired approach:
        Position = (Risk Amount) / (Risk Per Share)
        
        Args:
            portfolio_value: Total portfolio value
            entry_price: Entry price for the trade
            stop_loss_pct: Stop loss percentage (e.g., 0.05 for 5%)
            volatility: Stock volatility for ATR-based sizing
        
        Returns:
            Tuple of (shares, position_value)
        """
        stop_loss = stop_loss_pct or self.default_stop_loss
        
        # Method 1: Fixed fractional
        max_position_value = portfolio_value * self.max_position_pct
        
        # Method 2: Risk-based sizing
        risk_amount = portfolio_value * self.max_portfolio_risk
        risk_per_share = entry_price * stop_loss
        risk_based_shares = int(risk_amount / risk_per_share)
        risk_based_value = risk_based_shares * entry_price
        
        # Method 3: Volatility-adjusted (if volatility provided)
        if volatility and volatility > 0:
            # Inverse volatility scaling
            vol_factor = min(0.20 / volatility, 2.0)  # Cap at 2x
            vol_adjusted_value = max_position_value * vol_factor
        else:
            vol_adjusted_value = max_position_value
        
        # Take minimum of all methods
        final_value = min(max_position_value, risk_based_value, vol_adjusted_value)
        shares = max(1, int(final_value / entry_price))
        
        return shares, shares * entry_price
    
    def kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: float = 0.25  # Use fractional Kelly for safety
    ) -> float:
        """
        Calculate Kelly Criterion for position sizing
        
        Kelly % = W - [(1-W) / R]
        where W = win rate, R = win/loss ratio
        
        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average winning trade return
            avg_loss: Average losing trade return (positive number)
            fraction: Kelly fraction (0.25 = quarter Kelly)
        
        Returns:
            Recommended position size as fraction of portfolio
        """
        if avg_loss == 0:
            return 0
        
        win_loss_ratio = avg_win / avg_loss
        kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
        
        # Apply fractional Kelly and cap
        kelly = max(0, kelly * fraction)
        kelly = min(kelly, self.max_position_pct)
        
        return kelly


class PortfolioManager:
    """
    Manages portfolio positions and risk
    """
    
    def __init__(
        self,
        initial_capital: float = 100000,
        max_positions: int = 10,
        max_sector_exposure: float = 0.30,
        rebalance_threshold: float = 0.05
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.max_positions = max_positions
        self.max_sector_exposure = max_sector_exposure
        self.rebalance_threshold = rebalance_threshold
        
        self.positions: Dict[str, Position] = {}
        self.position_sizer = PositionSizer()
    
    def get_portfolio_value(self) -> float:
        """Get total portfolio value"""
        invested = sum(p.market_value for p in self.positions.values())
        return self.cash + invested
    
    def get_available_cash(self) -> float:
        """Get available cash for new positions"""
        return self.cash
    
    def can_open_position(self, symbol: str) -> bool:
        """Check if we can open a new position"""
        if symbol in self.positions:
            return False
        if len(self.positions) >= self.max_positions:
            return False
        return True
    
    def open_position(
        self,
        symbol: str,
        price: float,
        shares: Optional[int] = None,
        stop_loss_pct: float = 0.05
    ) -> Optional[Position]:
        """
        Open a new position
        
        Args:
            symbol: Stock symbol
            price: Entry price
            shares: Number of shares (calculated if not provided)
            stop_loss_pct: Stop loss percentage
        
        Returns:
            Position if successful, None otherwise
        """
        if not self.can_open_position(symbol):
            logger.warning(f"Cannot open position for {symbol}")
            return None
        
        portfolio_value = self.get_portfolio_value()
        
        if shares is None:
            shares, position_value = self.position_sizer.calculate_position_size(
                portfolio_value=portfolio_value,
                entry_price=price,
                stop_loss_pct=stop_loss_pct
            )
        else:
            position_value = shares * price
        
        if position_value > self.cash:
            shares = int(self.cash * 0.95 / price)
            position_value = shares * price
        
        if shares <= 0:
            logger.warning(f"Insufficient funds for {symbol}")
            return None
        
        # Execute trade
        self.cash -= position_value
        
        position = Position(
            symbol=symbol,
            shares=shares,
            entry_price=price,
            current_price=price,
            weight=position_value / portfolio_value,
            unrealized_pnl=0,
            unrealized_pnl_pct=0
        )
        
        self.positions[symbol] = position
        logger.info(f"Opened position: {shares} {symbol} @ ${price:.2f}")
        
        return position
    
    def close_position(self, symbol: str, price: float) -> Optional[float]:
        """
        Close a position
        
        Args:
            symbol: Stock symbol
            price: Exit price
        
        Returns:
            Realized P&L if successful, None otherwise
        """
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        proceeds = position.shares * price
        pnl = proceeds - (position.shares * position.entry_price)
        
        self.cash += proceeds
        del self.positions[symbol]
        
        logger.info(f"Closed position: {symbol} @ ${price:.2f} | PnL: ${pnl:.2f}")
        
        return pnl
    
    def update_prices(self, prices: Dict[str, float]):
        """
        Update position prices
        
        Args:
            prices: Dictionary mapping symbols to current prices
        """
        portfolio_value = self.get_portfolio_value()
        
        for symbol, position in self.positions.items():
            if symbol in prices:
                current_price = prices[symbol]
                position.current_price = current_price
                position.unrealized_pnl = (current_price - position.entry_price) * position.shares
                position.unrealized_pnl_pct = (current_price - position.entry_price) / position.entry_price
                position.weight = position.market_value / portfolio_value
    
    def calculate_risk_metrics(self, returns_data: Optional[Dict[str, pd.Series]] = None) -> RiskMetrics:
        """
        Calculate portfolio risk metrics
        
        Args:
            returns_data: Dictionary of historical returns for each position
        
        Returns:
            RiskMetrics object
        """
        portfolio_value = self.get_portfolio_value()
        invested = sum(p.market_value for p in self.positions.values())
        
        # Position weights
        weights = [p.weight for p in self.positions.values()]
        max_weight = max(weights) if weights else 0
        
        # Concentration risk (Herfindahl index)
        hhi = sum(w**2 for w in weights) if weights else 0
        
        # Calculate portfolio volatility and beta if returns provided
        portfolio_volatility = 0
        portfolio_beta = 1.0
        var_95 = 0
        
        if returns_data and self.positions:
            # Build portfolio returns
            position_symbols = list(self.positions.keys())
            position_weights = [self.positions[s].weight for s in position_symbols]
            
            # Filter to symbols we have returns for
            valid_symbols = [s for s in position_symbols if s in returns_data]
            if valid_symbols:
                returns_df = pd.DataFrame({s: returns_data[s] for s in valid_symbols}).dropna()
                
                if len(returns_df) > 20:
                    # Covariance matrix
                    cov_matrix = returns_df.cov() * 252
                    
                    # Portfolio volatility
                    w = np.array([self.positions[s].weight for s in valid_symbols])
                    w = w / w.sum()  # Normalize
                    portfolio_volatility = np.sqrt(w @ cov_matrix.values @ w)
                    
                    # Value at Risk (95%)
                    portfolio_returns = (returns_df * w).sum(axis=1)
                    var_95 = portfolio_value * np.percentile(portfolio_returns, 5) * np.sqrt(20)  # 20-day VaR
        
        return RiskMetrics(
            portfolio_value=portfolio_value,
            cash=self.cash,
            invested=invested,
            num_positions=len(self.positions),
            portfolio_beta=portfolio_beta,
            portfolio_volatility=portfolio_volatility,
            var_95=abs(var_95),
            max_position_weight=max_weight,
            concentration_risk=hhi
        )
    
    def get_positions_summary(self) -> pd.DataFrame:
        """Get a summary of all positions"""
        if not self.positions:
            return pd.DataFrame()
        
        data = []
        for symbol, pos in self.positions.items():
            data.append({
                "Symbol": symbol,
                "Shares": pos.shares,
                "Entry Price": f"${pos.entry_price:.2f}",
                "Current Price": f"${pos.current_price:.2f}",
                "Market Value": f"${pos.market_value:,.2f}",
                "Weight": f"{pos.weight:.1%}",
                "P&L": f"${pos.unrealized_pnl:,.2f}",
                "P&L %": f"{pos.unrealized_pnl_pct:.2%}"
            })
        
        return pd.DataFrame(data)
    
    def needs_rebalancing(self, target_weights: Dict[str, float]) -> bool:
        """Check if portfolio needs rebalancing"""
        for symbol, target in target_weights.items():
            if symbol in self.positions:
                current = self.positions[symbol].weight
                if abs(current - target) > self.rebalance_threshold:
                    return True
        return False


# Create instances
position_sizer = PositionSizer()
portfolio_manager = PortfolioManager()
