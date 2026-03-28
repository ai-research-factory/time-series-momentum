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
