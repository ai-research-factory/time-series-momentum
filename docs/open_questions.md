# Open Questions

## Ticker Availability
- **EWJ, BND, DBC, AUDUSD=X** are not available in the ARF Data API. Substitutes were used (EFA, AGG, SLV/UNG). This means the universe does not exactly match the paper's specification.
- **JPY=X** is not available; **USDJPY=X** is available but represents the inverse pair. Returns will need sign inversion when computing momentum signals for this currency.

## Data Considerations
- The paper uses futures data; this implementation uses ETF proxies. ETF returns may differ from futures due to roll costs, tracking error, and dividend reinvestment.
- The paper's full sample period starts from 1985. Our ETF data starts from 1993 (SPY) with most assets available only from 2002-2007, limiting the backtest period compared to the paper.
- Forward filling across non-trading days (e.g., currency markets trading on days equity markets are closed) may introduce small biases.

## VNQ Classification
- VNQ (Real Estate REIT) is classified under "commodities" for simplicity but could be argued as a separate asset class. This follows the paper's broad interpretation of alternative assets.

## Phase 3: Backtest Observations

### Sharpe Ratio Gap vs Paper
- Paper reports Sharpe ~1.0+ for diversified TSMOM portfolio. Our implementation yields 0.54 (gross). Likely causes:
  - Shorter data period (2007+ vs 1985+) — misses pre-GFC era where trend-following had strong performance
  - ETF proxies vs futures — different return dynamics, especially for commodities and currencies
  - Smaller universe (18 vs 55+ instruments in original paper)

### Vol Target Parameter
- Paper uses 40% annualized vol target per asset position. This is a high target and leads to significant leverage for low-vol assets (bonds, short-term treasuries). A 5x cap was applied to prevent extreme positions. The paper may use different capping or position sizing.

### USDJPY Sign Convention
- USDJPY=X returns have opposite sign convention to other currency pairs (EURUSD, GBPUSD). The momentum signal may need sign inversion for USDJPY to be consistent. This was not adjusted in Phase 3 to maintain simplicity; should be investigated in future phases.

### Transaction Cost Sensitivity
- 15 bps total cost (10 fee + 5 slippage) significantly erodes returns (Sharpe drops from 0.54 to 0.18). The vol-scaling approach generates frequent position changes as vol estimates update daily. The paper notes that futures transaction costs are lower than ETF costs.
