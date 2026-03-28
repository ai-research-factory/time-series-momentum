# Phase 5: Lookback Period Optimization — Technical Findings

## Objective

Evaluate the TSMOM strategy across multiple lookback periods and compare performance. Per the paper's analysis, the primary lookback is k=12 months. We evaluate near-neighbor periods: [6, 9, 12, 15, 18] months, converted to trading days using 21 days/month.

## Methodology

- **Lookback periods tested**: 6mo (126d), 9mo (189d), 12mo (252d), 15mo (315d), 18mo (378d)
- **Walk-forward validation**: 9 OOS windows per lookback, expanding training window
- **Transaction costs**: 10 bps fee + 5 bps slippage = 15 bps total
- **Vol scaling**: 60-day rolling vol, 40% annualized target (unchanged from Phase 3)
- **Data period**: 2007-04-18 to 2026-03-27 (18 assets, common period)

## Results

### Lookback Comparison Table

| Lookback | WF Gross Sharpe | WF Net Sharpe | Full Gross Sharpe | Full Net Sharpe | WF Avg Return | WF Max DD | Pos Windows | Trades |
|----------|----------------|---------------|-------------------|-----------------|---------------|-----------|-------------|--------|
| 6 mo     | 0.7529         | **0.2727**    | 0.7955            | **0.3633**      | 3.41%         | -38.5%    | 6/9 (67%)   | 2581   |
| 9 mo     | 0.3655         | -0.0742       | 0.4156            | 0.0324          | -1.10%        | -41.5%    | 4/9 (44%)   | 2432   |
| 12 mo    | 0.5894         | 0.1553        | 0.5410            | 0.1777          | 1.67%         | -34.8%    | 5/9 (56%)   | 2367   |
| 15 mo    | 0.3657         | -0.0183       | 0.3075            | -0.0159         | -0.52%        | -39.7%    | 6/9 (67%)   | 2236   |
| 18 mo    | 0.6111         | **0.2671**    | 0.5554            | **0.2613**      | 3.37%         | -36.7%    | 7/9 (78%)   | 2113   |

### Key Observations

1. **Best OOS performance**: 6-month lookback achieves the highest walk-forward net Sharpe (0.2727) and full-sample net Sharpe (0.3633). This is consistent with some literature suggesting shorter momentum lookbacks can be more responsive.

2. **Paper default (12mo) is middle-of-the-pack**: The 12-month lookback (paper's primary setting) ranks 3rd of 5 by WF net Sharpe. Its gross Sharpe (0.59) is reasonable but transaction costs erode it to 0.16 net.

3. **Non-monotonic relationship**: Performance does not monotonically increase or decrease with lookback length. The pattern is roughly U-shaped: 6mo and 18mo perform best, while 9mo and 15mo perform worst.

4. **18-month lookback has best stability**: 7/9 (78%) positive OOS windows, highest among all lookbacks, with lowest trade count (2113), meaning lower cost drag.

5. **Transaction cost sensitivity varies**: Shorter lookbacks generate more trades (2581 at 6mo vs 2113 at 18mo), but the 6mo lookback still outperforms net of costs due to stronger gross signal.

6. **9-month lookback underperforms**: Negative WF net Sharpe (-0.07), only 4/9 positive windows. This specific period creates signals that are too slow to capture short trends but too fast for long trends.

## Paper Consistency Analysis

The paper (Moskowitz, Ooi, Pedersen 2012) reports that:
- TSMOM is profitable across lookback horizons from 1 to 12 months
- 12-month lookback is the primary setting but 1-month also works well
- Shorter lookbacks tend to generate higher turnover but comparable Sharpe ratios

Our findings partially confirm this:
- The 12-month lookback produces positive gross Sharpe (0.54), consistent with the paper
- Shorter lookbacks (6mo) do produce stronger signals, consistent with the paper's finding that TSMOM exists across horizons
- The non-monotonic pattern at 9mo and 15mo may reflect our shorter data period (2007+ vs 1985+) and ETF proxy effects

## Limitations

- Only 5 lookback periods tested (paper-constrained near neighbors)
- ETF proxies vs futures may introduce lookback-dependent biases (e.g., dividend timing for equities)
- Common data period (2007+) misses pre-GFC era where longer lookbacks may have performed differently
- The 6-month lookback's superiority could be period-specific; it benefits from faster adaptation to post-GFC recovery and COVID rebound

## Conclusion

The TSMOM strategy is profitable across most lookback periods tested, with the notable exception of 9-month and 15-month windows. The paper's default 12-month lookback is a reasonable middle-ground choice. The 6-month lookback delivers the best OOS net Sharpe (0.27 vs 0.16 for 12mo), and the 18-month lookback offers the best stability (78% positive windows). These findings are classified as paper reproduction since all lookbacks tested are within the paper's specified near-neighbor range.
