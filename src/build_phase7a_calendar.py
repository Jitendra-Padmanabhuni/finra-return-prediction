"""Build the Phase 7A shared calendar from the acquired Yahoo cross-section."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", type=Path, default=Path("data/processed/phase7a_yahoo_alias_market.parquet"))
    parser.add_argument("--existing-market", type=Path, default=Path("data/processed/prototype_market_panel.csv"))
    parser.add_argument("--output", type=Path, default=Path("results/tables/phase7a_shared_market_dates.csv"))
    args = parser.parse_args()
    market = pd.read_parquet(args.market)
    counts = market.groupby("Date")["yahoo_symbol"].nunique().rename("market_symbols_present").reset_index().sort_values("Date")
    if counts["Date"].min() != pd.Timestamp("2022-09-01") or counts["Date"].max() != pd.Timestamp("2025-05-28"):
        raise ValueError("Historical Yahoo calendar does not cover the locked range and target session")
    if counts["market_symbols_present"].min() < 400:
        raise ValueError("A putative shared date has implausibly weak cross-sectional Yahoo coverage")
    existing = pd.read_csv(args.existing_market, parse_dates=["Date"])
    overlap_expected = set(existing.loc[existing["Date"].between("2025-01-15", "2025-05-28"), "Date"])
    overlap_observed = set(counts.loc[counts["Date"].between("2025-01-15", "2025-05-28"), "Date"])
    if overlap_expected != overlap_observed:
        raise ValueError("Historical calendar disagrees with the existing shared calendar in overlap")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    counts.to_csv(args.output, index=False)
    print(f"shared_dates={len(counts)}; min_symbols={counts.market_symbols_present.min()}; overlap_dates={len(overlap_expected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
