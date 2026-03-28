"""
Data loader for Time Series Momentum strategy.
Fetches daily price data from ARF Data API and processes into a unified DataFrame.
"""
import os
import time
import yaml
import pandas as pd
import requests
from pathlib import Path


API_BASE = "https://ai.1s.xyz/api/data/ohlcv"


class DataLoader:
    """Load and preprocess multi-asset price data from ARF Data API."""

    def __init__(self, config_path: str = "config/assets.yaml"):
        self.config_path = Path(config_path)
        self.tickers = self._load_tickers()

    def _load_tickers(self) -> list[str]:
        """Load ticker list from config YAML file."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        tickers = []
        for asset_class, symbols in config.items():
            if isinstance(symbols, list):
                tickers.extend(symbols)
        return tickers

    def _fetch_ticker(self, ticker: str, interval: str = "1d", period: str = "max") -> pd.Series:
        """Fetch OHLCV data for a single ticker from ARF Data API and return Close prices."""
        params = {"ticker": ticker, "interval": interval, "period": period}
        resp = requests.get(API_BASE, params=params, timeout=60)
        resp.raise_for_status()

        from io import StringIO
        df = pd.read_csv(StringIO(resp.text))
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp")

        # Use adjusted close if available, otherwise close
        if "adj_close" in df.columns:
            series = df["adj_close"]
        elif "close" in df.columns:
            series = df["close"]
        else:
            raise ValueError(f"No close price column found for {ticker}")

        series.name = ticker
        return series

    def fetch_all(self, interval: str = "1d", period: str = "max") -> pd.DataFrame:
        """Fetch price data for all tickers and combine into a single DataFrame."""
        all_prices = {}
        failed = []

        for ticker in self.tickers:
            print(f"Fetching {ticker}...")
            try:
                prices = self._fetch_ticker(ticker, interval=interval, period=period)
                all_prices[ticker] = prices
                print(f"  -> {len(prices)} rows")
                time.sleep(0.5)  # Rate limit
            except Exception as e:
                print(f"  -> FAILED: {e}")
                failed.append(ticker)

        if not all_prices:
            raise RuntimeError("No data fetched for any ticker")

        if failed:
            print(f"\nWarning: Failed to fetch {len(failed)} tickers: {failed}")

        # Combine into single DataFrame, aligned by date
        df = pd.DataFrame(all_prices)
        df.index.name = "date"
        df = df.sort_index()

        # Forward fill NaN values
        df = df.ffill()

        # Drop leading rows where all values are NaN
        df = df.dropna(how="all")

        return df, failed

    def save(self, df: pd.DataFrame, output_path: str = "data/processed/prices.parquet"):
        """Save processed DataFrame to parquet."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output)
        print(f"Saved {df.shape[0]} rows x {df.shape[1]} columns to {output}")

    def run(self, output_path: str = "data/processed/prices.parquet") -> pd.DataFrame:
        """Full pipeline: fetch all tickers, process, and save."""
        df, failed = self.fetch_all()
        self.save(df, output_path)
        return df
