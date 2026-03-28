"""
Time Series Momentum (TSMOM) strategy implementation.

Implements the paper's approach:
- Signal: sign of excess return over lookback period k (default 12 months = 252 days)
- Risk management: volatility scaling using 60-day rolling std dev
- Portfolio: equally weighted combination of individual volatility-scaled strategies
"""
import numpy as np
import pandas as pd
from pathlib import Path

# Paper defaults
DEFAULT_LOOKBACK = 252       # 12 months in trading days
DEFAULT_VOL_WINDOW = 60      # 60-day rolling volatility
DEFAULT_VOL_TARGET = 0.40    # 40% annualized vol target per asset (paper uses this)
TRADING_DAYS_PER_YEAR = 252


def compute_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute daily simple returns from price levels."""
    return prices.pct_change()


def compute_momentum_signal(returns: pd.DataFrame, lookback: int = DEFAULT_LOOKBACK) -> pd.DataFrame:
    """
    Compute time series momentum signal.

    Signal = sign of cumulative return over the lookback period.
    +1 = long, -1 = short.

    Per the paper, the signal is the sign of the excess return over the past k periods.
    We use the cumulative return (product of 1+r) - 1 over the lookback window.
    """
    cum_ret = (1 + returns).rolling(window=lookback).apply(
        lambda x: x.prod() - 1, raw=True
    )
    signal = np.sign(cum_ret)
    return signal


def compute_volatility_scaling(
    returns: pd.DataFrame,
    vol_window: int = DEFAULT_VOL_WINDOW,
    vol_target: float = DEFAULT_VOL_TARGET,
) -> pd.DataFrame:
    """
    Compute volatility scaling factors.

    Each asset is scaled by (vol_target / realized_vol) to target constant
    ex-ante volatility. Realized vol is annualized from daily rolling std.
    """
    daily_vol = returns.rolling(window=vol_window).std()
    annual_vol = daily_vol * np.sqrt(TRADING_DAYS_PER_YEAR)
    # Scaling factor: target / realized. Cap at 5x to avoid extreme leverage.
    scaling = (vol_target / annual_vol).clip(upper=5.0)
    return scaling


def construct_portfolio(
    returns: pd.DataFrame,
    signals: pd.DataFrame,
    vol_scaling: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construct volatility-scaled TSMOM portfolio.

    For each asset: strategy_return = signal(t-1) * vol_scale(t-1) * return(t)
    Signals and scaling are lagged by 1 day to avoid look-ahead bias.
    Portfolio return is the equal-weight average across all assets.

    Returns a DataFrame with columns:
    - Individual asset strategy returns
    - 'portfolio': equal-weight portfolio return
    """
    # Lag signals and vol_scaling by 1 to avoid look-ahead
    lagged_signals = signals.shift(1)
    lagged_scaling = vol_scaling.shift(1)

    # Individual strategy returns: signal * vol_scale * asset_return
    strategy_returns = lagged_signals * lagged_scaling * returns

    # Equal-weight portfolio: mean across assets (ignoring NaN)
    portfolio_return = strategy_returns.mean(axis=1)

    result = strategy_returns.copy()
    result["portfolio"] = portfolio_return
    return result


def compute_positions(signals: pd.DataFrame, vol_scaling: pd.DataFrame) -> pd.DataFrame:
    """
    Compute effective positions (signal * vol_scaling) for cost calculation.
    Lagged by 1 day (positions determined at end of day t-1, applied at day t).
    """
    return (signals * vol_scaling).shift(1)


def run_strategy(
    prices: pd.DataFrame,
    lookback: int = DEFAULT_LOOKBACK,
    vol_window: int = DEFAULT_VOL_WINDOW,
    vol_target: float = DEFAULT_VOL_TARGET,
) -> dict:
    """
    Run the full TSMOM strategy on price data.

    Args:
        prices: DataFrame of daily prices (columns = assets)
        lookback: Momentum lookback period in trading days
        vol_window: Volatility estimation window
        vol_target: Annualized volatility target per asset

    Returns:
        dict with keys:
        - 'returns': daily asset returns
        - 'signals': momentum signals (+1/-1)
        - 'vol_scaling': volatility scaling factors
        - 'strategy_returns': individual + portfolio strategy returns
        - 'positions': effective positions for cost calculation
    """
    returns = compute_returns(prices)
    signals = compute_momentum_signal(returns, lookback=lookback)
    vol_scaling = compute_volatility_scaling(returns, vol_window=vol_window, vol_target=vol_target)
    strategy_returns = construct_portfolio(returns, signals, vol_scaling)
    positions = compute_positions(signals, vol_scaling)

    return {
        "returns": returns,
        "signals": signals,
        "vol_scaling": vol_scaling,
        "strategy_returns": strategy_returns,
        "positions": positions,
    }


def load_prices(path: str = "data/processed/prices.parquet") -> pd.DataFrame:
    """Load price data from parquet file."""
    return pd.read_parquet(path)
