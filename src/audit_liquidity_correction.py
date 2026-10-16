"""Audit corrected exact-20-date liquidity universes against legacy output."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def ranked(frame: pd.DataFrame, median_name: str, count_name: str) -> pd.DataFrame:
    output = frame.sort_values([median_name, "source_symbol"], ascending=[False, True]).copy()
    output["rank"] = range(1, len(output) + 1)
    output["selected"] = output["rank"].le(400)
    return output.rename(columns={median_name: "median_dollar_volume", count_name: "valid_observations"})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", type=Path, default=Path("data/processed/prototype_market_panel.csv"))
    parser.add_argument("--corrected", type=Path, default=Path("data/processed/prototype_universe_monthly.csv"))
    parser.add_argument("--legacy", type=Path, default=Path("legacy/expanding_liquidity_window/data_processed/prototype_universe_monthly.csv"))
    parser.add_argument("--tables-dir", type=Path, default=Path("results/tables"))
    args = parser.parse_args()
    market = pd.read_csv(args.market, parse_dates=["Date"])
    market["dollar_volume"] = market["Close"] * market["Volume"]
    corrected_selected = pd.read_csv(args.corrected, parse_dates=["rebalance_date"])
    legacy_selected = pd.read_csv(args.legacy, parse_dates=["rebalance_date"])
    trade_dates = market["Date"].drop_duplicates().sort_values().reset_index(drop=True)
    comparisons = []
    validations = []

    for rebalance_date in corrected_selected["rebalance_date"].drop_duplicates().sort_values():
        location = int(trade_dates.searchsorted(rebalance_date))
        window_dates = trade_dates.iloc[location - 20 : location]
        assert len(window_dates) == 20
        assert window_dates.max() < rebalance_date
        assert window_dates.min() == trade_dates.iloc[location - 20]

        exact_rows = market.loc[market["Date"].isin(window_dates), ["source_symbol", "Date", "Close", "Volume", "dollar_volume"]].copy()
        exact_rows["valid"] = exact_rows[["Close", "Volume"]].notna().all(axis=1)
        exact = exact_rows.groupby("source_symbol", as_index=False).agg(
            exact_valid=("valid", "sum"),
            exact_dates=("Date", "nunique"),
            exact_median=("dollar_volume", "median"),
        )
        exact = exact.loc[exact["exact_valid"].eq(20) & exact["exact_dates"].eq(20)]
        exact = ranked(exact, "exact_median", "exact_valid").rename(columns={
            "median_dollar_volume": "corrected_median_dollar_volume",
            "valid_observations": "corrected_valid_observations",
            "rank": "corrected_rank",
            "selected": "corrected_selected",
        })

        legacy_rows = market.loc[market["Date"] < rebalance_date, ["source_symbol", "dollar_volume"]]
        legacy = legacy_rows.groupby("source_symbol", as_index=False)["dollar_volume"].agg(
            legacy_valid="count", legacy_median="median"
        )
        legacy = legacy.loc[legacy["legacy_valid"].ge(20)]
        legacy = ranked(legacy, "legacy_median", "legacy_valid").rename(columns={
            "median_dollar_volume": "legacy_median_dollar_volume",
            "valid_observations": "legacy_valid_observations",
            "rank": "legacy_rank",
            "selected": "legacy_selected",
        })

        compare = exact.merge(legacy, on="source_symbol", how="outer", validate="one_to_one")
        compare["corrected_selected"] = compare["corrected_selected"].eq(True)
        compare["legacy_selected"] = compare["legacy_selected"].eq(True)
        compare["rebalance_date"] = rebalance_date
        compare["selection_change"] = "unchanged_not_selected"
        compare.loc[compare["corrected_selected"] & compare["legacy_selected"], "selection_change"] = "overlap"
        compare.loc[compare["corrected_selected"] & ~compare["legacy_selected"], "selection_change"] = "added_corrected"
        compare.loc[~compare["corrected_selected"] & compare["legacy_selected"], "selection_change"] = "removed_corrected"
        compare["median_dollar_volume_change"] = compare["corrected_median_dollar_volume"] - compare["legacy_median_dollar_volume"]
        compare["rank_change_corrected_minus_legacy"] = compare["corrected_rank"] - compare["legacy_rank"]
        comparisons.append(compare)

        corrected_names = set(compare.loc[compare["corrected_selected"], "source_symbol"])
        legacy_names = set(compare.loc[compare["legacy_selected"], "source_symbol"])
        actual_corrected_names = set(corrected_selected.loc[corrected_selected["rebalance_date"].eq(rebalance_date), "source_symbol"])
        actual_legacy_names = set(legacy_selected.loc[legacy_selected["rebalance_date"].eq(rebalance_date), "source_symbol"])
        assert corrected_names == actual_corrected_names
        assert legacy_names == actual_legacy_names
        assert len(corrected_names) == 400 if len(exact) >= 400 else len(corrected_names) == len(exact)
        overlap = len(corrected_names & legacy_names)
        union = len(corrected_names | legacy_names)
        validations.append({
            "rebalance_date": rebalance_date,
            "window_shared_date_count": len(window_dates),
            "window_min_date": window_dates.min(),
            "window_max_date": window_dates.max(),
            "window_max_strictly_before_rebalance": bool(window_dates.max() < rebalance_date),
            "older_observations_contributed": False,
            "corrected_eligible": len(exact),
            "corrected_selected": len(corrected_names),
            "legacy_selected": len(legacy_names),
            "overlap": overlap,
            "added_corrected": len(corrected_names - legacy_names),
            "removed_corrected": len(legacy_names - corrected_names),
            "jaccard_similarity": overlap / union,
            "all_corrected_eligible_have_20_valid": bool(exact["corrected_valid_observations"].eq(20).all()),
        })

    full = pd.concat(comparisons, ignore_index=True)
    affected = full.loc[full["selection_change"].isin(["added_corrected", "removed_corrected"])].copy()
    validation = pd.DataFrame(validations)
    args.tables_dir.mkdir(parents=True, exist_ok=True)
    validation.to_csv(args.tables_dir / "phase2_liquidity_correction_monthly_comparison.csv", index=False)
    affected.to_csv(args.tables_dir / "phase2_liquidity_correction_affected_securities.csv", index=False)
    full.to_csv(args.tables_dir / "phase2_liquidity_correction_full_rank_comparison.csv", index=False)
    print(validation.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
