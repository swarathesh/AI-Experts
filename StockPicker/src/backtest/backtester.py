"""
Backtesting Engine
Simulates trading strategies on historical data
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from loguru import logger
from datetime import datetime


@dataclass
class Trade:
    """Represents a single trade"""
    symbol: str
    entry_date: datetime
    entry_price: float
    shares: int
    direction: str  # 'long' or 'short'
    exit_date: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    
    @property
    def is_open(self) -> bool:
        return self.exit_date is None


@dataclass
class BacktestResult:
    """Results from a backtest"""
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    avg_trade_duration: float
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=pd.Series)
    
    def to_dict(self) -> Dict:
        return {
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "total_return": self.total_return,
            "total_return_pct": f"{self.total_return_pct:.2%}",
            "annualized_return": f"{self.annualized_return:.2%}",
            "max_drawdown": f"{self.max_drawdown:.2%}",
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "win_rate": f"{self.win_rate:.2%}",
            "profit_factor": self.profit_factor,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "avg_win": f"{self.avg_win:.2%}",
            "avg_loss": f"{self.avg_loss:.2%}",
            "avg_trade_duration": f"{self.avg_trade_duration:.1f} days"
        }
    
    def print_summary(self):
        """Print a formatted summary of results"""
        print("\n" + "="*50)
        print("BACKTEST RESULTS")
        print("="*50)
        print(f"Initial Capital:    ${self.initial_capital:,.2f}")
        print(f"Final Capital:      ${self.final_capital:,.2f}")
        print(f"Total Return:       ${self.total_return:,.2f} ({self.total_return_pct:.2%})")
        print(f"Annualized Return:  {self.annualized_return:.2%}")
        print("-"*50)
        print(f"Max Drawdown:       {self.max_drawdown:.2%}")
        print(f"Sharpe Ratio:       {self.sharpe_ratio:.2f}")
        print(f"Sortino Ratio:      {self.sortino_ratio:.2f}")
        print("-"*50)
        print(f"Total Trades:       {self.total_trades}")
        print(f"Win Rate:           {self.win_rate:.2%}")
        print(f"Profit Factor:      {self.profit_factor:.2f}")
        print(f"Avg Win:            {self.avg_win:.2%}")
        print(f"Avg Loss:           {self.avg_loss:.2%}")
        print(f"Avg Trade Duration: {self.avg_trade_duration:.1f} days")
        print("="*50 + "\n")


class Backtester:
    """
    Backtesting engine for trading strategies
    """
    
    def __init__(
        self,
        initial_capital: float = 100000,
        commission: float = 0.001,  # 0.1%
        slippage: float = 0.001,    # 0.1%
        max_position_size: float = 0.1,  # 10% max per position
        stop_loss: Optional[float] = 0.05,  # 5% stop loss
        take_profit: Optional[float] = 0.15  # 15% take profit
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.max_position_size = max_position_size
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        
        self.reset()
    
    def reset(self):
        """Reset the backtester state"""
        self.cash = self.initial_capital
        self.positions: Dict[str, Trade] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.dates: List[datetime] = []
    
    def run(
        self,
        data: Dict[str, pd.DataFrame],
        signal_func: Callable[[pd.DataFrame, str], int]
    ) -> BacktestResult:
        """
        Run backtest on historical data
        
        Args:
            data: Dictionary mapping symbols to DataFrames with OHLCV + indicators
            signal_func: Function that takes (df, symbol) and returns signal (-1, 0, 1)
        
        Returns:
            BacktestResult with performance metrics
        """
        self.reset()
        
        # Get common date range across all symbols
        all_dates = set()
        for symbol, df in data.items():
            all_dates.update(df.index.tolist())
        all_dates = sorted(all_dates)
        
        logger.info(f"Running backtest from {all_dates[0]} to {all_dates[-1]}")
        logger.info(f"Testing {len(data)} symbols")
        
        # Iterate through each day
        for date in all_dates:
            # Update positions and check stops
            self._update_positions(data, date)
            
            # Generate signals and execute trades
            for symbol, df in data.items():
                if date not in df.index:
                    continue
                
                # Get data up to current date (no lookahead)
                historical = df.loc[:date]
                
                if len(historical) < 20:  # Need minimum data
                    continue
                
                # Get signal
                signal = signal_func(historical, symbol)
                
                # Execute trade based on signal
                current_price = df.loc[date, 'close']
                self._execute_signal(symbol, signal, current_price, date)
            
            # Record equity
            portfolio_value = self._calculate_portfolio_value(data, date)
            self.equity_curve.append(portfolio_value)
            self.dates.append(date)
        
        # Close all remaining positions
        self._close_all_positions(data, all_dates[-1])
        
        # Calculate metrics
        return self._calculate_results()
    
    def _execute_signal(self, symbol: str, signal: int, price: float, date: datetime):
        """Execute a trading signal"""
        
        # Apply slippage
        if signal == 1:
            execution_price = price * (1 + self.slippage)
        elif signal == -1:
            execution_price = price * (1 - self.slippage)
        else:
            execution_price = price
        
        # Current position
        current_position = self.positions.get(symbol)
        
        if signal == 1 and current_position is None:
            # Open long position
            position_value = min(
                self.cash * self.max_position_size,
                self.cash * 0.95  # Keep some cash buffer
            )
            shares = int(position_value / execution_price)
            
            if shares > 0:
                cost = shares * execution_price * (1 + self.commission)
                
                if cost <= self.cash:
                    self.cash -= cost
                    self.positions[symbol] = Trade(
                        symbol=symbol,
                        entry_date=date,
                        entry_price=execution_price,
                        shares=shares,
                        direction='long'
                    )
                    logger.debug(f"BUY {shares} {symbol} @ ${execution_price:.2f}")
        
        elif signal == -1 and current_position is not None:
            # Close long position
            self._close_position(symbol, execution_price, date)
    
    def _close_position(self, symbol: str, price: float, date: datetime):
        """Close an open position"""
        if symbol not in self.positions:
            return
        
        trade = self.positions[symbol]
        trade.exit_date = date
        trade.exit_price = price
        
        # Calculate P&L
        proceeds = trade.shares * price * (1 - self.commission)
        cost = trade.shares * trade.entry_price
        trade.pnl = proceeds - cost
        trade.pnl_pct = trade.pnl / cost
        
        self.cash += proceeds
        self.trades.append(trade)
        del self.positions[symbol]
        
        logger.debug(f"SELL {trade.shares} {symbol} @ ${price:.2f} | PnL: ${trade.pnl:.2f} ({trade.pnl_pct:.2%})")
    
    def _update_positions(self, data: Dict[str, pd.DataFrame], date: datetime):
        """Update positions and check stop loss / take profit"""
        symbols_to_close = []
        
        for symbol, trade in self.positions.items():
            if symbol not in data or date not in data[symbol].index:
                continue
            
            current_price = data[symbol].loc[date, 'close']
            current_return = (current_price - trade.entry_price) / trade.entry_price
            
            # Check stop loss
            if self.stop_loss and current_return <= -self.stop_loss:
                symbols_to_close.append((symbol, current_price, "stop_loss"))
            
            # Check take profit
            elif self.take_profit and current_return >= self.take_profit:
                symbols_to_close.append((symbol, current_price, "take_profit"))
        
        # Close positions outside loop
        for symbol, price, reason in symbols_to_close:
            logger.debug(f"Closing {symbol} due to {reason}")
            self._close_position(symbol, price, date)
    
    def _close_all_positions(self, data: Dict[str, pd.DataFrame], date: datetime):
        """Close all remaining positions"""
        for symbol in list(self.positions.keys()):
            if symbol in data and date in data[symbol].index:
                price = data[symbol].loc[date, 'close']
                self._close_position(symbol, price, date)
    
    def _calculate_portfolio_value(self, data: Dict[str, pd.DataFrame], date: datetime) -> float:
        """Calculate total portfolio value"""
        value = self.cash
        
        for symbol, trade in self.positions.items():
            if symbol in data and date in data[symbol].index:
                current_price = data[symbol].loc[date, 'close']
                value += trade.shares * current_price
        
        return value
    
    def _calculate_results(self) -> BacktestResult:
        """Calculate backtest metrics"""
        equity = pd.Series(self.equity_curve, index=self.dates)
        returns = equity.pct_change().dropna()
        
        # Basic metrics
        final_capital = equity.iloc[-1] if len(equity) > 0 else self.initial_capital
        total_return = final_capital - self.initial_capital
        total_return_pct = total_return / self.initial_capital
        
        # Annualized return
        if len(self.dates) > 1:
            days = (self.dates[-1] - self.dates[0]).days
            years = days / 365.25
            annualized_return = (1 + total_return_pct) ** (1 / max(years, 0.01)) - 1
        else:
            annualized_return = 0
        
        # Drawdown
        rolling_max = equity.expanding().max()
        drawdown = (equity - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # Sharpe ratio (assuming 252 trading days, 0% risk-free rate)
        if len(returns) > 0 and returns.std() > 0:
            sharpe_ratio = np.sqrt(252) * returns.mean() / returns.std()
        else:
            sharpe_ratio = 0
        
        # Sortino ratio (downside deviation)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0 and downside_returns.std() > 0:
            sortino_ratio = np.sqrt(252) * returns.mean() / downside_returns.std()
        else:
            sortino_ratio = 0
        
        # Trade statistics
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]
        
        total_trades = len(self.trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        avg_win = np.mean([t.pnl_pct for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl_pct for t in losing_trades]) if losing_trades else 0
        
        # Average trade duration
        durations = []
        for t in self.trades:
            if t.exit_date and t.entry_date:
                durations.append((t.exit_date - t.entry_date).days)
        avg_duration = np.mean(durations) if durations else 0
        
        return BacktestResult(
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_return_pct=total_return_pct,
            annualized_return=annualized_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            avg_win=avg_win,
            avg_loss=avg_loss,
            avg_trade_duration=avg_duration,
            trades=self.trades,
            equity_curve=equity
        )


# Create instance
backtester = Backtester()
