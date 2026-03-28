"""
Run TSMOM backtest with walk-forward validation.

Uses the standard backtest framework from src/backtest.py and the
strategy implementation from src/strategy.py.
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

from src.backtest import (
    BacktestConfig,
    BacktestResult,
    WalkForwardValidator,
    calculate_costs,
    compute_metrics,
    generate_metrics_json,
)
from src.strategy import (
    run_strategy,
    load_prices,
    compute_returns,
    compute_momentum_signal,
    compute_volatility_scaling,
    construct_portfolio,
    compute_positions,
    DEFAULT_LOOKBACK,
    DEFAULT_VOL_WINDOW,
    DEFAULT_VOL_TARGET,
    TRADING_DAYS_PER_YEAR,
)


def run_walk_forward_backtest(
    prices: pd.DataFrame,
    config: BacktestConfig | None = None,
    lookback: int = DEFAULT_LOOKBACK,
    vol_window: int = DEFAULT_VOL_WINDOW,
    vol_target: float = DEFAULT_VOL_TARGET,
) -> tuple[list[BacktestResult], pd.Series, pd.Series]:
    """
    Run walk-forward TSMOM backtest.

    For each walk-forward window:
    1. Use training period to establish signal and vol parameters
       (no fitting needed - signals are computed from rolling windows)
    2. Evaluate on test period

    Since TSMOM is a rule-based strategy with no fitted parameters,
    we compute signals over the full dataset (using only past data via
    rolling windows) and then evaluate on out-of-sample windows.

    Returns:
        Tuple of (results, full_gross_returns, full_net_returns)
    """
    if config is None:
        config = BacktestConfig()

    # Compute strategy over full dataset (signals only use past data)
    strat = run_strategy(prices, lookback=lookback, vol_window=vol_window, vol_target=vol_target)
    portfolio_returns = strat["strategy_returns"]["portfolio"]
    positions = strat["positions"]

    # Aggregate positions for cost calc: sum of absolute position changes across assets
    avg_position = positions.mean(axis=1)

    # Drop NaN rows (warmup period for lookback + vol window)
    valid_mask = portfolio_returns.notna()
    portfolio_returns = portfolio_returns[valid_mask]
    avg_position = avg_position.reindex(portfolio_returns.index).fillna(0)

    # Walk-forward validation
    validator = WalkForwardValidator(config)
    results = []

    full_gross = pd.Series(dtype=float)
    full_net = pd.Series(dtype=float)

    for train_idx, test_idx in validator.split(portfolio_returns.to_frame()):
        test_returns = portfolio_returns.iloc[test_idx]
        test_positions = avg_position.iloc[test_idx]

        if len(test_returns) == 0:
            continue

        # Gross metrics
        gross_metrics = compute_metrics(test_returns)

        # Net returns (after costs)
        net_returns = calculate_costs(test_returns, test_positions, config)
        net_metrics = compute_metrics(net_returns)

        # Count trades: days where position changes
        trades = test_positions.diff().abs()
        total_trades = int((trades > 0.01).sum())

        result = BacktestResult(
            window=len(results),
            train_start=str(portfolio_returns.index[train_idx[0]].date()),
            train_end=str(portfolio_returns.index[train_idx[-1]].date()),
            test_start=str(test_returns.index[0].date()),
            test_end=str(test_returns.index[-1].date()),
            gross_sharpe=gross_metrics["sharpeRatio"],
            net_sharpe=net_metrics["sharpeRatio"],
            annual_return=net_metrics["annualReturn"],
            max_drawdown=net_metrics["maxDrawdown"],
            total_trades=total_trades,
            hit_rate=net_metrics["hitRate"],
            pnl_series=net_returns,
        )
        results.append(result)
        full_gross = pd.concat([full_gross, test_returns])
        full_net = pd.concat([full_net, net_returns])

    return results, full_gross, full_net


def run_full_sample_backtest(
    prices: pd.DataFrame,
    config: BacktestConfig | None = None,
    lookback: int = DEFAULT_LOOKBACK,
    vol_window: int = DEFAULT_VOL_WINDOW,
    vol_target: float = DEFAULT_VOL_TARGET,
) -> dict:
    """
    Run strategy over full sample and compute aggregate metrics.
    Used for reporting full-sample statistics alongside walk-forward OOS.
    """
    if config is None:
        config = BacktestConfig()

    strat = run_strategy(prices, lookback=lookback, vol_window=vol_window, vol_target=vol_target)
    portfolio_returns = strat["strategy_returns"]["portfolio"].dropna()
    positions = strat["positions"].mean(axis=1).reindex(portfolio_returns.index).fillna(0)

    gross_metrics = compute_metrics(portfolio_returns)
    net_returns = calculate_costs(portfolio_returns, positions, config)
    net_metrics = compute_metrics(net_returns)

    trades = positions.diff().abs()
    total_trades = int((trades > 0.01).sum())

    return {
        "gross": gross_metrics,
        "net": net_metrics,
        "total_trades": total_trades,
        "n_days": len(portfolio_returns),
        "start_date": str(portfolio_returns.index[0].date()),
        "end_date": str(portfolio_returns.index[-1].date()),
    }


def run_asset_class_breakdown(
    prices: pd.DataFrame,
    asset_classes: dict[str, list[str]],
    lookback: int = DEFAULT_LOOKBACK,
    vol_window: int = DEFAULT_VOL_WINDOW,
    vol_target: float = DEFAULT_VOL_TARGET,
) -> dict:
    """Compute full-sample metrics per asset class."""
    strat = run_strategy(prices, lookback=lookback, vol_window=vol_window, vol_target=vol_target)
    strategy_rets = strat["strategy_returns"]

    breakdown = {}
    for cls_name, tickers in asset_classes.items():
        available = [t for t in tickers if t in strategy_rets.columns]
        if not available:
            continue
        cls_returns = strategy_rets[available].mean(axis=1).dropna()
        if len(cls_returns) > 0:
            metrics = compute_metrics(cls_returns)
            breakdown[cls_name] = metrics
    return breakdown


def main():
    """Main entry point for running the TSMOM backtest."""
    import yaml

    print("=" * 60)
    print("Time Series Momentum - Phase 3 Backtest")
    print("=" * 60)

    # Load prices
    prices = load_prices()
    print(f"\nLoaded prices: {prices.shape[0]} rows x {prices.shape[1]} assets")
    print(f"Date range: {prices.index[0].date()} to {prices.index[-1].date()}")

    # Use common period where all assets have data
    common_start = max(prices[col].first_valid_index() for col in prices.columns)
    prices_common = prices.loc[common_start:].copy()
    print(f"Common period: {prices_common.index[0].date()} to {prices_common.index[-1].date()}")
    print(f"Common period rows: {len(prices_common)}")

    # Load asset class mapping
    with open("config/assets.yaml") as f:
        asset_config = yaml.safe_load(f)
    asset_classes = {k: v for k, v in asset_config.items() if isinstance(v, list)}

    config = BacktestConfig()

    # 1. Walk-forward backtest
    print("\n--- Walk-Forward Backtest ---")
    results, full_gross, full_net = run_walk_forward_backtest(prices_common, config)

    for r in results:
        print(f"  Window {r.window}: test={r.test_start} to {r.test_end}, "
              f"gross_sharpe={r.gross_sharpe:.4f}, net_sharpe={r.net_sharpe:.4f}")

    # 2. Full-sample metrics
    print("\n--- Full Sample Metrics ---")
    full_sample = run_full_sample_backtest(prices_common, config)
    print(f"  Gross Sharpe: {full_sample['gross']['sharpeRatio']:.4f}")
    print(f"  Net Sharpe:   {full_sample['net']['sharpeRatio']:.4f}")
    print(f"  Annual Return: {full_sample['net']['annualReturn']:.4f}")
    print(f"  Max Drawdown:  {full_sample['net']['maxDrawdown']:.4f}")
    print(f"  Hit Rate:      {full_sample['net']['hitRate']:.4f}")
    print(f"  Total Trades:  {full_sample['total_trades']}")

    # 3. Asset class breakdown
    print("\n--- Asset Class Breakdown (Full Sample, Gross) ---")
    breakdown = run_asset_class_breakdown(prices_common, asset_classes)
    for cls_name, metrics in breakdown.items():
        print(f"  {cls_name}: Sharpe={metrics['sharpeRatio']:.4f}, "
              f"Return={metrics['annualReturn']:.4f}")

    # 4. Generate metrics.json
    custom_metrics = {
        "phase": "backtest_vol_scaling",
        "lookbackDays": DEFAULT_LOOKBACK,
        "volWindow": DEFAULT_VOL_WINDOW,
        "volTarget": DEFAULT_VOL_TARGET,
        "commonPeriodStart": str(prices_common.index[0].date()),
        "commonPeriodEnd": str(prices_common.index[-1].date()),
        "totalAssets": prices_common.shape[1],
        "fullSampleGrossSharpe": full_sample["gross"]["sharpeRatio"],
        "fullSampleNetSharpe": full_sample["net"]["sharpeRatio"],
        "fullSampleAnnualReturn": full_sample["net"]["annualReturn"],
        "fullSampleMaxDrawdown": full_sample["net"]["maxDrawdown"],
        "assetClassBreakdown": breakdown,
    }

    metrics_json = generate_metrics_json(results, config, custom_metrics)

    # Save reports
    report_dir = Path("reports/cycle_3")
    report_dir.mkdir(parents=True, exist_ok=True)

    with open(report_dir / "metrics.json", "w") as f:
        json.dump(metrics_json, f, indent=2)
    print(f"\nSaved metrics to {report_dir / 'metrics.json'}")

    # Return for use in technical findings
    return {
        "results": results,
        "full_sample": full_sample,
        "breakdown": breakdown,
        "metrics_json": metrics_json,
        "config": config,
    }


if __name__ == "__main__":
    main()
