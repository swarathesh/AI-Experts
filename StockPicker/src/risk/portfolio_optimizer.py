"""
Portfolio Optimization Module
Mean-Variance Optimization, Risk Parity, and other allocation strategies
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

try:
    import cvxpy as cp
    CVXPY_AVAILABLE = True
except ImportError:
    CVXPY_AVAILABLE = False
    logger.warning("CVXPY not available. Install with: pip install cvxpy")

from scipy.optimize import minimize


@dataclass
class OptimizationResult:
    """Result from portfolio optimization"""
    weights: Dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    method: str
    
    def to_dict(self) -> Dict:
        return {
            "weights": self.weights,
            "expected_return": f"{self.expected_return:.2%}",
            "volatility": f"{self.volatility:.2%}",
            "sharpe_ratio": f"{self.sharpe_ratio:.2f}",
            "method": self.method
        }
    
    def print_allocation(self):
        """Print allocation summary"""
        print("\n" + "="*50)
        print(f"  PORTFOLIO OPTIMIZATION ({self.method})")
        print("="*50)
        print(f"\n  Expected Return: {self.expected_return:.2%}")
        print(f"  Volatility:      {self.volatility:.2%}")
        print(f"  Sharpe Ratio:    {self.sharpe_ratio:.2f}")
        print("\n  Allocation:")
        print("-"*50)
        for symbol, weight in sorted(self.weights.items(), key=lambda x: -x[1]):
            if weight > 0.001:  # Only show meaningful allocations
                print(f"    {symbol:8} {weight:>6.1%}")
        print("="*50 + "\n")


class PortfolioOptimizer:
    """
    Portfolio optimization using various methods:
    - Mean-Variance (Markowitz)
    - Maximum Sharpe Ratio
    - Minimum Volatility
    - Risk Parity
    - Black-Litterman (with views)
    """
    
    def __init__(self, risk_free_rate: float = 0.05):
        """
        Initialize optimizer
        
        Args:
            risk_free_rate: Annual risk-free rate for Sharpe calculations
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_statistics(
        self,
        returns: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate expected returns and covariance matrix
        
        Args:
            returns: DataFrame of historical returns (each column is a stock)
        
        Returns:
            Tuple of (expected_returns, covariance_matrix)
        """
        # Annualized expected returns
        expected_returns = returns.mean() * 252
        
        # Annualized covariance matrix
        cov_matrix = returns.cov() * 252
        
        return expected_returns.values, cov_matrix.values
    
    def optimize_max_sharpe(
        self,
        returns: pd.DataFrame,
        constraints: Optional[Dict] = None
    ) -> OptimizationResult:
        """
        Find the portfolio with maximum Sharpe ratio
        
        Args:
            returns: DataFrame of historical returns
            constraints: Optional constraints (min_weight, max_weight, sector_limits)
        
        Returns:
            OptimizationResult with optimal weights
        """
        symbols = returns.columns.tolist()
        n = len(symbols)
        
        expected_returns, cov_matrix = self.calculate_statistics(returns)
        
        # Default constraints
        if constraints is None:
            constraints = {}
        
        min_weight = constraints.get('min_weight', 0.0)
        max_weight = constraints.get('max_weight', 0.4)
        
        if CVXPY_AVAILABLE:
            return self._optimize_cvxpy(
                symbols, expected_returns, cov_matrix,
                'max_sharpe', min_weight, max_weight
            )
        else:
            return self._optimize_scipy(
                symbols, expected_returns, cov_matrix,
                'max_sharpe', min_weight, max_weight
            )
    
    def optimize_min_volatility(
        self,
        returns: pd.DataFrame,
        constraints: Optional[Dict] = None
    ) -> OptimizationResult:
        """
        Find the minimum volatility portfolio
        
        Args:
            returns: DataFrame of historical returns
            constraints: Optional constraints
        
        Returns:
            OptimizationResult
        """
        symbols = returns.columns.tolist()
        expected_returns, cov_matrix = self.calculate_statistics(returns)
        
        constraints = constraints or {}
        min_weight = constraints.get('min_weight', 0.0)
        max_weight = constraints.get('max_weight', 0.4)
        
        if CVXPY_AVAILABLE:
            return self._optimize_cvxpy(
                symbols, expected_returns, cov_matrix,
                'min_vol', min_weight, max_weight
            )
        else:
            return self._optimize_scipy(
                symbols, expected_returns, cov_matrix,
                'min_vol', min_weight, max_weight
            )
    
    def optimize_risk_parity(
        self,
        returns: pd.DataFrame
    ) -> OptimizationResult:
        """
        Risk parity allocation - equal risk contribution from each asset
        
        Args:
            returns: DataFrame of historical returns
        
        Returns:
            OptimizationResult
        """
        symbols = returns.columns.tolist()
        n = len(symbols)
        
        expected_returns, cov_matrix = self.calculate_statistics(returns)
        
        def risk_contribution(weights):
            """Calculate risk contribution of each asset"""
            portfolio_vol = np.sqrt(weights @ cov_matrix @ weights)
            marginal_risk = cov_matrix @ weights
            risk_contrib = weights * marginal_risk / portfolio_vol
            return risk_contrib
        
        def objective(weights):
            """Minimize deviation from equal risk contribution"""
            risk_contrib = risk_contribution(weights)
            target_risk = np.ones(n) / n
            return np.sum((risk_contrib - target_risk)**2)
        
        # Initial weights
        x0 = np.ones(n) / n
        
        # Constraints
        constraints_list = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        ]
        bounds = [(0.01, 0.5) for _ in range(n)]
        
        result = minimize(
            objective, x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints_list
        )
        
        weights = result.x
        weights = weights / weights.sum()  # Normalize
        
        port_return = weights @ expected_returns
        port_vol = np.sqrt(weights @ cov_matrix @ weights)
        sharpe = (port_return - self.risk_free_rate) / port_vol
        
        return OptimizationResult(
            weights=dict(zip(symbols, weights)),
            expected_return=port_return,
            volatility=port_vol,
            sharpe_ratio=sharpe,
            method="Risk Parity"
        )
    
    def optimize_target_return(
        self,
        returns: pd.DataFrame,
        target_return: float,
        constraints: Optional[Dict] = None
    ) -> OptimizationResult:
        """
        Find minimum volatility portfolio for a target return
        
        Args:
            returns: DataFrame of historical returns
            target_return: Target annual return
            constraints: Optional constraints
        
        Returns:
            OptimizationResult
        """
        symbols = returns.columns.tolist()
        n = len(symbols)
        
        expected_returns, cov_matrix = self.calculate_statistics(returns)
        
        constraints = constraints or {}
        min_weight = constraints.get('min_weight', 0.0)
        max_weight = constraints.get('max_weight', 0.5)
        
        if CVXPY_AVAILABLE:
            # CVXPY optimization
            weights = cp.Variable(n)
            
            portfolio_return = expected_returns @ weights
            portfolio_vol = cp.quad_form(weights, cov_matrix)
            
            objective = cp.Minimize(portfolio_vol)
            
            constraints_list = [
                cp.sum(weights) == 1,
                weights >= min_weight,
                weights <= max_weight,
                portfolio_return >= target_return
            ]
            
            problem = cp.Problem(objective, constraints_list)
            
            try:
                problem.solve()
                
                if problem.status == 'optimal':
                    w = weights.value
                    port_return = w @ expected_returns
                    port_vol = np.sqrt(w @ cov_matrix @ w)
                    sharpe = (port_return - self.risk_free_rate) / port_vol
                    
                    return OptimizationResult(
                        weights=dict(zip(symbols, w)),
                        expected_return=port_return,
                        volatility=port_vol,
                        sharpe_ratio=sharpe,
                        method=f"Target Return ({target_return:.0%})"
                    )
            except:
                pass
        
        # Fallback to scipy
        return self._optimize_scipy(
            symbols, expected_returns, cov_matrix,
            'target_return', min_weight, max_weight, target_return
        )
    
    def efficient_frontier(
        self,
        returns: pd.DataFrame,
        n_points: int = 50
    ) -> pd.DataFrame:
        """
        Calculate the efficient frontier
        
        Args:
            returns: DataFrame of historical returns
            n_points: Number of points on the frontier
        
        Returns:
            DataFrame with return, volatility, sharpe for each point
        """
        expected_returns, cov_matrix = self.calculate_statistics(returns)
        
        min_ret = expected_returns.min()
        max_ret = expected_returns.max()
        
        target_returns = np.linspace(min_ret, max_ret, n_points)
        
        results = []
        for target in target_returns:
            try:
                result = self.optimize_target_return(returns, target)
                results.append({
                    'target_return': target,
                    'return': result.expected_return,
                    'volatility': result.volatility,
                    'sharpe': result.sharpe_ratio
                })
            except:
                continue
        
        return pd.DataFrame(results)
    
    def _optimize_cvxpy(
        self,
        symbols: List[str],
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        objective_type: str,
        min_weight: float,
        max_weight: float
    ) -> OptimizationResult:
        """Optimization using CVXPY"""
        n = len(symbols)
        weights = cp.Variable(n)
        
        portfolio_return = expected_returns @ weights
        portfolio_vol = cp.quad_form(weights, cov_matrix)
        
        constraints = [
            cp.sum(weights) == 1,
            weights >= min_weight,
            weights <= max_weight
        ]
        
        if objective_type == 'max_sharpe':
            # Maximize Sharpe = maximize return for unit risk
            # Use auxiliary variable for Sharpe ratio optimization
            objective = cp.Maximize(portfolio_return - 0.5 * portfolio_vol)
        elif objective_type == 'min_vol':
            objective = cp.Minimize(portfolio_vol)
        else:
            objective = cp.Minimize(portfolio_vol)
        
        problem = cp.Problem(objective, constraints)
        problem.solve()
        
        if problem.status != 'optimal':
            logger.warning(f"Optimization status: {problem.status}")
        
        w = weights.value
        w = np.maximum(w, 0)  # Ensure non-negative
        w = w / w.sum()  # Normalize
        
        port_return = w @ expected_returns
        port_vol = np.sqrt(w @ cov_matrix @ w)
        sharpe = (port_return - self.risk_free_rate) / port_vol if port_vol > 0 else 0
        
        method = "Max Sharpe" if objective_type == 'max_sharpe' else "Min Volatility"
        
        return OptimizationResult(
            weights=dict(zip(symbols, w)),
            expected_return=port_return,
            volatility=port_vol,
            sharpe_ratio=sharpe,
            method=method
        )
    
    def _optimize_scipy(
        self,
        symbols: List[str],
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        objective_type: str,
        min_weight: float,
        max_weight: float,
        target_return: float = None
    ) -> OptimizationResult:
        """Optimization using scipy (fallback)"""
        n = len(symbols)
        
        def portfolio_return(weights):
            return weights @ expected_returns
        
        def portfolio_volatility(weights):
            return np.sqrt(weights @ cov_matrix @ weights)
        
        def neg_sharpe(weights):
            ret = portfolio_return(weights)
            vol = portfolio_volatility(weights)
            return -(ret - self.risk_free_rate) / vol if vol > 0 else 0
        
        # Initial weights
        x0 = np.ones(n) / n
        
        # Bounds
        bounds = [(min_weight, max_weight) for _ in range(n)]
        
        # Constraints
        constraints_list = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        ]
        
        if objective_type == 'target_return' and target_return is not None:
            constraints_list.append({
                'type': 'eq',
                'fun': lambda x: portfolio_return(x) - target_return
            })
        
        # Objective
        if objective_type == 'max_sharpe':
            objective = neg_sharpe
        else:
            objective = portfolio_volatility
        
        result = minimize(
            objective, x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints_list
        )
        
        w = result.x
        w = np.maximum(w, 0)
        w = w / w.sum()
        
        port_return = w @ expected_returns
        port_vol = np.sqrt(w @ cov_matrix @ w)
        sharpe = (port_return - self.risk_free_rate) / port_vol if port_vol > 0 else 0
        
        method_map = {
            'max_sharpe': 'Max Sharpe (SciPy)',
            'min_vol': 'Min Volatility (SciPy)',
            'target_return': f'Target Return (SciPy)'
        }
        
        return OptimizationResult(
            weights=dict(zip(symbols, w)),
            expected_return=port_return,
            volatility=port_vol,
            sharpe_ratio=sharpe,
            method=method_map.get(objective_type, 'Unknown')
        )
    
    def black_litterman(
        self,
        returns: pd.DataFrame,
        market_caps: Dict[str, float],
        views: Dict[str, float],
        view_confidences: Dict[str, float],
        tau: float = 0.05
    ) -> OptimizationResult:
        """
        Black-Litterman model incorporating investor views
        
        Args:
            returns: DataFrame of historical returns
            market_caps: Market capitalizations for each symbol
            views: Expected returns for specific assets (views)
            view_confidences: Confidence in each view (0-1)
            tau: Scaling factor for uncertainty
        
        Returns:
            OptimizationResult
        """
        symbols = returns.columns.tolist()
        n = len(symbols)
        
        # Prior returns and covariance
        _, cov_matrix = self.calculate_statistics(returns)
        
        # Market-cap weights for equilibrium returns
        total_cap = sum(market_caps.get(s, 1) for s in symbols)
        market_weights = np.array([market_caps.get(s, 1) / total_cap for s in symbols])
        
        # Implied equilibrium returns (reverse optimization)
        delta = 2.5  # Risk aversion coefficient
        pi = delta * cov_matrix @ market_weights
        
        # View matrix P (which assets are we making views on)
        view_symbols = list(views.keys())
        k = len(view_symbols)
        
        if k == 0:
            # No views - return market-cap weighted portfolio
            port_return = market_weights @ pi
            port_vol = np.sqrt(market_weights @ cov_matrix @ market_weights)
            sharpe = (port_return - self.risk_free_rate) / port_vol
            
            return OptimizationResult(
                weights=dict(zip(symbols, market_weights)),
                expected_return=port_return,
                volatility=port_vol,
                sharpe_ratio=sharpe,
                method="Black-Litterman (No Views)"
            )
        
        P = np.zeros((k, n))
        Q = np.zeros(k)
        
        for i, symbol in enumerate(view_symbols):
            if symbol in symbols:
                P[i, symbols.index(symbol)] = 1
                Q[i] = views[symbol]
        
        # Uncertainty in views (omega)
        omega = np.diag([
            (1 - view_confidences.get(s, 0.5)) * tau * P[i] @ cov_matrix @ P[i].T
            for i, s in enumerate(view_symbols)
        ])
        
        # Black-Litterman posterior
        tau_cov = tau * cov_matrix
        
        # Posterior expected returns
        inv_tau_cov = np.linalg.inv(tau_cov)
        inv_omega = np.linalg.inv(omega + 1e-10 * np.eye(k))
        
        posterior_cov = np.linalg.inv(inv_tau_cov + P.T @ inv_omega @ P)
        posterior_mean = posterior_cov @ (inv_tau_cov @ pi + P.T @ inv_omega @ Q)
        
        # Optimize with posterior estimates
        weights = self._optimize_scipy(
            symbols, posterior_mean, cov_matrix,
            'max_sharpe', 0.0, 0.4
        ).weights
        
        w = np.array([weights[s] for s in symbols])
        port_return = w @ posterior_mean
        port_vol = np.sqrt(w @ cov_matrix @ w)
        sharpe = (port_return - self.risk_free_rate) / port_vol
        
        return OptimizationResult(
            weights=weights,
            expected_return=port_return,
            volatility=port_vol,
            sharpe_ratio=sharpe,
            method="Black-Litterman"
        )


# Create instance
portfolio_optimizer = PortfolioOptimizer()
