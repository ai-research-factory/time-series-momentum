# Cycle 2: Data Pipeline Construction - Technical Findings

## Implementation

### DataLoader (`src/data_loader.py`)
- `DataLoader` class reads ticker configuration from `config/assets.yaml`
- Fetches daily OHLCV data from the ARF Data API (`https://ai.1s.xyz/api/data/ohlcv`)
- Extracts `adj_close` (or `close` as fallback) for each ticker
- Combines all series into a single DataFrame aligned by date
- Forward fills NaN values to handle non-trading days across different markets
- Saves output as Parquet to `data/processed/prices.parquet`

### Asset Universe (18 tickers across 4 asset classes)
| Asset Class | Tickers | Count |
|---|---|---|
| Equities | SPY, QQQ, EFA, EEM, IWM | 5 |
| Bonds | TLT, IEF, SHY, AGG, LQD | 5 |
| Commodities | GLD, SLV, USO, UNG, VNQ | 5 |
| Currencies | EURUSD=X, GBPUSD=X, USDJPY=X | 3 |

### Ticker Substitutions
The following tickers from the paper's design brief were not available in the ARF Data API:
- **EWJ** (Japan ETF) -> substituted with **EFA** (International Developed Markets)
- **BND** (Total Bond) -> substituted with **AGG** (US Aggregate Bond)
- **DBC** (Commodities) -> not available; added **SLV**, **UNG** as additional commodity exposure
- **JPY=X** -> substituted with **USDJPY=X** (inverse pair)
- **AUDUSD=X** -> not available in API; dropped

Additional tickers added to reach ~20 assets: IWM, SHY, LQD, SLV, UNG, VNQ.

## Data Quality

### Coverage
- **Date range**: 1993-01-29 to 2026-03-27 (33+ years)
- **Total rows**: 8,617 trading days
- **All 18 tickers fetched successfully** (0 failures)

### Missing Data
Missing values exist in early years before ETF inception dates. Forward fill handles gaps from non-trading days. Leading NaN values remain for tickers with later start dates:
- Earliest: SPY (1993), USDJPY=X (1996)
- Latest: UNG (2007)
- Effective common period with all assets: 2007-04-18 onward (~19 years)

## Output
- `data/processed/prices.parquet`: 8,617 rows x 18 columns
