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


def run_lookback_optimization(
    prices: pd.DataFrame,
    lookback_months: list[int] | None = None,
    config: BacktestConfig | None = None,
    vol_window: int = DEFAULT_VOL_WINDOW,
    vol_target: float = DEFAULT_VOL_TARGET,
) -> dict:
    """
    Evaluate the strategy across multiple lookback periods.

    Per the paper's analysis, the primary lookback is 12 months.
    We evaluate near-neighbor periods: [6, 9, 12, 15, 18] months.

    Args:
        prices: DataFrame of daily prices
        lookback_months: List of lookback periods in months (default [6,9,12,15,18])
        config: Backtest configuration
        vol_window: Volatility estimation window
        vol_target: Annualized volatility target

    Returns:
        Dict with keys:
        - 'results_by_lookback': {lookback_days: {walk_forward results, full_sample results}}
        - 'best_lookback': lookback with best OOS net Sharpe
        - 'summary': comparison table as list of dicts
    """
    if lookback_months is None:
        lookback_months = [6, 9, 12, 15, 18]
    if config is None:
        config = BacktestConfig()

    # Convert months to trading days (21 trading days per month)
    TRADING_DAYS_PER_MONTH = 21
    lookback_days_list = [m * TRADING_DAYS_PER_MONTH for m in lookback_months]

    results_by_lookback = {}
    summary = []

    for months, lookback_days in zip(lookback_months, lookback_days_list):
        print(f"\n  Lookback = {months} months ({lookback_days} days)...")

        # Walk-forward backtest
        wf_results, full_gross, full_net = run_walk_forward_backtest(
            prices, config, lookback=lookback_days, vol_window=vol_window, vol_target=vol_target
        )

        # Full-sample backtest
        full_sample = run_full_sample_backtest(
            prices, config, lookback=lookback_days, vol_window=vol_window, vol_target=vol_target
        )

        # Aggregate walk-forward metrics
        if wf_results:
            avg_gross_sharpe = float(np.mean([r.gross_sharpe for r in wf_results]))
            avg_net_sharpe = float(np.mean([r.net_sharpe for r in wf_results]))
            avg_annual_return = float(np.mean([r.annual_return for r in wf_results]))
            worst_drawdown = float(min(r.max_drawdown for r in wf_results))
            positive_windows = sum(1 for r in wf_results if r.net_sharpe > 0)
            n_windows = len(wf_results)
            total_trades = sum(r.total_trades for r in wf_results)
        else:
            avg_gross_sharpe = avg_net_sharpe = avg_annual_return = 0.0
            worst_drawdown = 0.0
            positive_windows = n_windows = total_trades = 0

        entry = {
            "lookback_months": months,
            "lookback_days": lookback_days,
            "wf_avg_gross_sharpe": round(avg_gross_sharpe, 4),
            "wf_avg_net_sharpe": round(avg_net_sharpe, 4),
            "wf_avg_annual_return": round(avg_annual_return, 4),
            "wf_worst_drawdown": round(worst_drawdown, 4),
            "wf_positive_windows": positive_windows,
            "wf_total_windows": n_windows,
            "wf_total_trades": total_trades,
            "full_gross_sharpe": full_sample["gross"]["sharpeRatio"],
            "full_net_sharpe": full_sample["net"]["sharpeRatio"],
            "full_annual_return": full_sample["net"]["annualReturn"],
            "full_max_drawdown": full_sample["net"]["maxDrawdown"],
        }
        summary.append(entry)

        results_by_lookback[lookback_days] = {
            "wf_results": wf_results,
            "full_sample": full_sample,
            "metrics": entry,
        }

        print(f"    WF Net Sharpe: {avg_net_sharpe:.4f}, "
              f"Full Net Sharpe: {full_sample['net']['sharpeRatio']:.4f}, "
              f"Positive: {positive_windows}/{n_windows}")

    # Find best lookback by WF avg net Sharpe
    best = max(summary, key=lambda x: x["wf_avg_net_sharpe"])
    best_lookback = best["lookback_days"]

    return {
        "results_by_lookback": results_by_lookback,
        "best_lookback": best_lookback,
        "best_lookback_months": best["lookback_months"],
        "summary": summary,
    }


def main():
    """Main entry point for running the TSMOM backtest."""
    import yaml

    print("=" * 60)
    print("Time Series Momentum - Phase 5 Lookback Optimization")
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

    # 1. Lookback optimization across [6, 9, 12, 15, 18] months
    print("\n--- Lookback Period Optimization ---")
    opt = run_lookback_optimization(prices_common, config=config)

    # Print summary table
    print("\n--- Summary Table ---")
    print(f"{'Lookback':>10} {'WF Gross':>10} {'WF Net':>10} {'Full Gross':>10} "
          f"{'Full Net':>10} {'WF Return':>10} {'WF MaxDD':>10} {'Pos Win':>8} {'Trades':>8}")
    for s in opt["summary"]:
        print(f"{s['lookback_months']:>7}mo  "
              f"{s['wf_avg_gross_sharpe']:>10.4f} {s['wf_avg_net_sharpe']:>10.4f} "
              f"{s['full_gross_sharpe']:>10.4f} {s['full_net_sharpe']:>10.4f} "
              f"{s['wf_avg_annual_return']:>10.4f} {s['wf_worst_drawdown']:>10.4f} "
              f"{s['wf_positive_windows']:>3}/{s['wf_total_windows']:<3} "
              f"{s['wf_total_trades']:>8}")

    best_months = opt["best_lookback_months"]
    best_days = opt["best_lookback"]
    print(f"\nBest lookback by WF net Sharpe: {best_months} months ({best_days} days)")

    # 2. Run detailed walk-forward for the paper's default (12 months) for primary metrics
    print("\n--- Paper Default (12 months) Walk-Forward Details ---")
    default_data = opt["results_by_lookback"][252]
    default_wf_results = default_data["wf_results"]
    for r in default_wf_results:
        print(f"  Window {r.window}: test={r.test_start} to {r.test_end}, "
              f"gross_sharpe={r.gross_sharpe:.4f}, net_sharpe={r.net_sharpe:.4f}")

    # 3. Full-sample for paper default
    full_sample = default_data["full_sample"]
    print(f"\n  Full-Sample Gross Sharpe: {full_sample['gross']['sharpeRatio']:.4f}")
    print(f"  Full-Sample Net Sharpe:   {full_sample['net']['sharpeRatio']:.4f}")

    # 4. Asset class breakdown at paper default
    print("\n--- Asset Class Breakdown (12mo, Full Sample, Gross) ---")
    breakdown = run_asset_class_breakdown(prices_common, asset_classes)
    for cls_name, metrics in breakdown.items():
        print(f"  {cls_name}: Sharpe={metrics['sharpeRatio']:.4f}, "
              f"Return={metrics['annualReturn']:.4f}")

    # 5. Generate metrics.json — primary metrics use paper default (12mo)
    # Best lookback results stored in customMetrics
    best_data = opt["results_by_lookback"][best_days]

    custom_metrics = {
        "phase": "lookback_optimization",
        "paperDefaultLookbackDays": DEFAULT_LOOKBACK,
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
        "lookbackComparison": opt["summary"],
        "bestLookbackMonths": best_months,
        "bestLookbackDays": best_days,
        "bestLookbackWfNetSharpe": best_data["metrics"]["wf_avg_net_sharpe"],
        "bestLookbackFullNetSharpe": best_data["full_sample"]["net"]["sharpeRatio"],
    }

    metrics_json = generate_metrics_json(default_wf_results, config, custom_metrics)

    # Save reports
    report_dir = Path("reports/cycle_5")
    report_dir.mkdir(parents=True, exist_ok=True)

    with open(report_dir / "metrics.json", "w") as f:
        json.dump(metrics_json, f, indent=2)
    print(f"\nSaved metrics to {report_dir / 'metrics.json'}")

    # Return for use in technical findings
    return {
        "optimization": opt,
        "full_sample": full_sample,
        "breakdown": breakdown,
        "metrics_json": metrics_json,
        "config": config,
    }


if __name__ == "__main__":
    main()
