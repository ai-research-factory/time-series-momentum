# Phase 3: Basic Backtest and Volatility Scaling — Technical Findings

## Implementation Summary

Implemented a vectorized TSMOM (Time Series Momentum) backtester with volatility scaling and walk-forward validation.

### New Modules
- **`src/strategy.py`**: Core strategy implementation
  - `compute_momentum_signal()`: Rolling cumulative return sign over lookback period
  - `compute_volatility_scaling()`: 60-day rolling vol with annualized target scaling
  - `construct_portfolio()`: Equal-weight combination with 1-day lag to prevent look-ahead
  - `run_strategy()`: Full pipeline from prices to portfolio returns
- **`src/run_backtest.py`**: Backtest runner with walk-forward validation
  - Uses `WalkForwardValidator` from `src/backtest.py`
  - Computes both gross and net-of-cost metrics
  - Asset class breakdown analysis

### Paper Parameters (Faithfully Reproduced)
| Parameter | Paper Default | Implementation |
|-----------|--------------|----------------|
| Lookback (k) | 12 months | 252 trading days |
| Vol window | 60 days | 60 days |
| Vol target | 40% annualized | 40% annualized |
| Rebalance freq | Daily | Daily |
| Portfolio weighting | Equal weight | Equal weight |

## Results

### Full-Sample Performance (2007-04-18 to 2026-03-27)
| Metric | Gross | Net (15 bps) |
|--------|-------|-------------|
| Sharpe Ratio | 0.5410 | 0.1777 |
| Annual Return | 4.86% | 1.55% |
| Max Drawdown | -38.73% | -42.40% |
| Hit Rate | 52.71% | 52.71% |

### Walk-Forward Out-of-Sample (9 windows)
| Metric | Value |
|--------|-------|
| Windows | 9 |
| Positive Windows | 5 (55.6%) |
| Avg OOS Net Sharpe | 0.1553 |
| Best Window Net Sharpe | 1.0254 |
| Worst Window Net Sharpe | -0.6666 |

### Asset Class Breakdown (Full Sample, Gross)
| Asset Class | Sharpe | Annual Return | Max Drawdown |
|-------------|--------|---------------|--------------|
| Equities | 0.3362 | 5.76% | -64.75% |
| Bonds | 0.3365 | 5.00% | -48.84% |
| Commodities | 0.4661 | 8.10% | -44.60% |
| Currencies | 0.0464 | -2.02% | -65.12% |

## Observations

1. **Positive but modest Sharpe**: Full-sample gross Sharpe of 0.54 is positive but below the paper's reported ~1.0+. This is expected given our shorter data period (2007+ vs 1985+), use of ETF proxies instead of futures, and smaller universe.

2. **Transaction costs matter significantly**: The 15 bps round-trip cost reduces Sharpe from 0.54 to 0.18. The vol-scaling strategy generates frequent position adjustments, amplifying cost drag.

3. **Commodities lead**: Commodities showed the strongest momentum signal (Sharpe 0.47), consistent with the paper's finding that commodity trend-following is robust.

4. **Currencies underperform**: Currency momentum is weakest (Sharpe 0.05), partially due to USDJPY=X being an inverse pair (documented in open_questions.md).

5. **Walk-forward stability**: 5 out of 9 OOS windows are positive (55.6%), showing the signal is present but not uniformly strong across all market regimes.

6. **Vol-scaling caps**: Position sizes are capped at 5x leverage to prevent extreme positions when realized volatility is very low (e.g., SHY short-term treasuries).

## Methodology Notes

- **No look-ahead bias**: Signals use only past returns (rolling window). Signals and vol-scaling are lagged by 1 day before applying to returns.
- **Walk-forward validation**: 9 expanding windows with 70/30 train/test split, minimum 252-day training period, 1-day gap.
- **Cost model**: 10 bps fee + 5 bps slippage applied to absolute position changes.
