# Phase 6: Asset Class Decomposition — Technical Findings

## Objective

Decompose the TSMOM strategy performance by asset class (equities, bonds, commodities, currencies) to validate robustness. The paper finds that TSMOM generates positive returns across all asset classes, with diversification providing significant Sharpe ratio improvement over individual classes.

## Methodology

- **Lookback**: 12 months (252 trading days) — paper default
- **Volatility scaling**: 60-day rolling std, 40% annualized target, 5x cap
- **Rebalancing**: Daily
- **Costs**: 10 bps fee + 5 bps slippage = 15 bps total
- **Validation**: Walk-forward with 9 expanding windows (70/30 split)
- **Period**: 2007-04-18 to 2026-03-27 (common period, all 18 assets)

## Results

### 1. Asset Class Walk-Forward Summary

| Class        | Assets | WF Gross Sharpe | WF Net Sharpe | Positive Windows | Full Gross Sharpe | Full Net Sharpe | Full MaxDD |
|-------------|--------|-----------------|---------------|------------------|-------------------|-----------------|-----------|
| **Equities**    | 5  | 0.3555          | **0.2015**    | **7/9 (78%)**    | 0.3362            | 0.2060          | -77.0%    |
| **Bonds**       | 5  | 0.2093          | -0.1681       | 3/9 (33%)        | 0.3365            | 0.0084          | -71.1%    |
| **Commodities** | 5  | **0.4100**      | 0.1718        | 5/9 (56%)        | **0.4661**        | **0.2567**      | -58.5%    |
| **Currencies**  | 3  | 0.1731          | -0.2914       | 4/9 (44%)        | 0.0464            | -0.3777         | -91.4%    |
| **Portfolio**   | 18 | 0.5894          | 0.1553        | 5/9 (56%)        | 0.5410            | 0.1777          | -42.4%    |

**Key observations:**
- **Commodities** achieve the highest gross Sharpe (0.47) and best net performance (0.26 full-sample net Sharpe)
- **Equities** are the most stable: 7/9 positive OOS windows (78%) despite lower absolute Sharpe
- **Bonds** show positive gross performance but costs erode returns to near-zero net
- **Currencies** are the weakest class with negative net Sharpe — consistent with the smaller universe (3 vs 5 assets) and ETF proxy issues

### 2. Individual Asset Performance (Full Sample, Gross)

**Top performers by Sharpe:**
1. SHY (Short-term Treasury): 1.0155 — anomalously high due to low volatility + stable trend
2. SPY (S&P 500): 0.4789
3. QQQ (NASDAQ 100): 0.4750
4. SLV (Silver): 0.4129
5. GLD (Gold): 0.4115

**Worst performers:**
1. EURUSD=X: -0.2341
2. USO (Crude Oil): -0.0707
3. GBPUSD=X: -0.0162
4. TLT (Long-term Treasury): 0.0407
5. VNQ (Real Estate): 0.0572

**Within-class dispersion:**
- Equities: High dispersion (SPY/QQQ ~0.48 vs EEM 0.07). US large-cap momentum is strong; international/EM is weak.
- Bonds: Extreme dispersion (SHY 1.02 vs TLT 0.04). Short-duration bonds show strong TSMOM; long-duration does not.
- Commodities: Moderate dispersion (GLD/SLV ~0.41 vs USO -0.07). Precious metals trend well; crude oil does not.
- Currencies: High dispersion (USDJPY 0.33 vs EURUSD -0.23). Only USDJPY shows positive momentum.

### 3. Diversification Analysis

**Correlation matrix of asset class sub-portfolios:**

|              | Equities | Bonds  | Commodities | Currencies |
|-------------|----------|--------|-------------|------------|
| Equities    | 1.0000   | 0.0127 | 0.2698      | 0.0180     |
| Bonds       | 0.0127   | 1.0000 | 0.1527      | 0.0845     |
| Commodities | 0.2698   | 0.1527 | 1.0000      | 0.0462     |
| Currencies  | 0.0180   | 0.0845 | 0.0462      | 1.0000     |

- All pairwise correlations are **low** (0.01 to 0.27), confirming strong diversification potential
- Highest correlation: equities-commodities (0.27) — likely driven by risk-on/risk-off dynamics
- Lowest correlation: equities-bonds (0.01) — near-zero, ideal for diversification

**Diversification ratio:**
- Portfolio Sharpe: 0.5091
- Average class Sharpe: 0.2963
- **Diversification ratio: 1.72x** — the diversified portfolio achieves 72% higher Sharpe than the average individual class

This confirms the paper's finding that cross-asset diversification is a key driver of TSMOM portfolio performance.

### 4. Comparison with Paper

The paper (Moskowitz, Ooi, Pedersen 2012) reports:
- Positive TSMOM returns across all asset classes
- Commodities and currencies as strong performers
- Diversified portfolio Sharpe ~1.0+

Our findings:
- **Consistent**: Commodities are the strongest class (same as paper)
- **Divergent**: Currencies are the weakest class (paper finds them strong — likely due to our limited 3-asset universe vs paper's full FX futures universe)
- **Consistent**: Diversification significantly improves Sharpe (1.72x ratio)
- **Divergent**: Overall Sharpe lower (0.54 gross vs ~1.0) due to shorter data period (2007+ vs 1985+) and ETF proxies

### 5. Robustness Assessment

**Strategy is robust across asset classes (3 of 4 classes profitable gross):**
- Equities: Robust (positive gross and net, 78% positive windows)
- Commodities: Robust (highest Sharpe, positive net)
- Bonds: Marginally positive (gross OK, net near zero due to high turnover costs)
- Currencies: Not robust (negative net, limited universe)

**Transaction cost sensitivity is class-dependent:**
- Equities cost drag: ~0.13 Sharpe points (moderate)
- Bonds cost drag: ~0.33 Sharpe points (high — frequent vol-driven rebalancing)
- Commodities cost drag: ~0.21 Sharpe points (moderate)
- Currencies cost drag: ~0.42 Sharpe points (severe — high turnover, low gross signal)

## Implementation Details

New functions added to `src/run_backtest.py`:
- `run_asset_class_walk_forward()`: Walk-forward validation per asset class sub-portfolio with cost accounting
- `run_individual_asset_analysis()`: Full-sample gross metrics for each individual asset
- `run_diversification_analysis()`: Cross-class correlation matrix and diversification ratio computation

All analysis uses the paper's default parameters (12-month lookback, 60-day vol window, 40% vol target).
