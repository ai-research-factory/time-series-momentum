#!/usr/bin/env python3
"""Download and process multi-asset price data for Time Series Momentum strategy."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.data_loader import DataLoader


def main():
    loader = DataLoader(config_path=project_root / "config" / "assets.yaml")
    df = loader.run(output_path=project_root / "data" / "processed" / "prices.parquet")

    print(f"\nSummary:")
    print(f"  Date range: {df.index.min()} to {df.index.max()}")
    print(f"  Assets: {df.shape[1]}")
    print(f"  Rows: {df.shape[0]}")
    print(f"  Missing values: {df.isna().sum().sum()}")


if __name__ == "__main__":
    main()
