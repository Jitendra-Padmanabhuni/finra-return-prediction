"""Build Phase 3 prototype master panel with explicit left-join statuses only."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from inspect_finra import read_finra_file


def parse_candidate_finra(raw_dir: Path, dates: pd.Series, mappings: pd.DataFrame) -> pd.DataFrame:
    wanted = set(mappings["finra_symbol"])
    rows = []
    for date in dates.drop_duplicates().sort_values():
        path = raw_dir / f"CNMSshvol{pd.Timestamp(date):%Y%m%d}.txt"
        if not path.exists():
            continue
        records, _ = read_finra_file(path)
        for record in records:
            if record["Symbol"] in wanted:
                rows.append({"Date": pd.Timestamp(record["Date"]), "finra_symbol": record["Symbol"],
                             "ShortVolume": record["ShortVolume"], "ShortExemptVolume": record["ShortExemptVolume"],
                             "TotalVolume": record["TotalVolume"], "finra_market": record["Market"],
                             "finra_source_file": path.name})
    result = pd.DataFrame(rows)
    if result.duplicated(["Date", "finra_symbol"]).any():
        raise ValueError("FINRA candidate observations are not unique by date/symbol")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", default=Path("data/raw"), type=Path)
    parser.add_argument("--processed-dir", default=Path("data/processed"), type=Path)
    parser.add_argument("--tables-dir", default=Path("results/tables"), type=Path)
    args = parser.parse_args()
    universe = pd.read_csv(args.processed_dir / "prototype_universe_daily.csv", parse_dates=["Date"])
    market = pd.read_csv(args.processed_dir / "prototype_market_panel.csv", parse_dates=["Date"])
    candidates = pd.read_csv(args.tables_dir / "phase2_candidate_universe.csv")
    mappings = candidates[["source_symbol", "yahoo_symbol"]].rename(columns={"source_symbol": "canonical_research_symbol"})
    mappings["finra_symbol"] = mappings["canonical_research_symbol"]
    mappings.loc[mappings["canonical_research_symbol"] == "BRK.B", "finra_symbol"] = "BRK/B"
    mappings.loc[mappings["canonical_research_symbol"] == "BF.B", "finra_symbol"] = "BF/B"
    spine = universe.rename(columns={"source_symbol": "canonical_research_symbol", "yahoo_symbol": "universe_yahoo_symbol"})
    if spine.duplicated(["Date", "canonical_research_symbol"]).any():
        raise ValueError("Expected spine is not unique")
    market = market.rename(columns={"source_symbol": "canonical_research_symbol", "yahoo_symbol": "market_yahoo_symbol"})
    if market.duplicated(["Date", "canonical_research_symbol"]).any():
        raise ValueError("Market data is not unique")
    finra = parse_candidate_finra(args.raw_dir, market["Date"], mappings)
    finra = finra.merge(mappings[["canonical_research_symbol", "finra_symbol"]], on="finra_symbol", how="left", validate="many_to_one")
    panel = spine.merge(market, on=["Date", "canonical_research_symbol"], how="left", validate="one_to_one", indicator="market_join")
    panel = panel.merge(finra, on=["Date", "canonical_research_symbol"], how="left", validate="one_to_one", indicator="finra_join")
    panel["market_observation_present"] = panel["market_join"].eq("both")
    panel["finra_observation_present"] = panel["finra_join"].eq("both")
    panel["symbol_mapping_status"] = "mapped"
    panel.loc[panel["canonical_research_symbol"].isin(["BRK.B", "BF.B"]), "symbol_mapping_status"] = "explicit_finra_slash_and_yahoo_hyphen_mapping"
    panel["join_status"] = "complete_match"
    panel.loc[~panel["finra_observation_present"] & panel["market_observation_present"], "join_status"] = "missing_finra_observation"
    panel.loc[panel["finra_observation_present"] & ~panel["market_observation_present"], "join_status"] = "missing_market_observation"
    panel.loc[~panel["finra_observation_present"] & ~panel["market_observation_present"], "join_status"] = "other_excluded_or_unresolved_observation"
    if panel.duplicated(["Date", "canonical_research_symbol"]).any() or len(panel) != len(spine):
        raise ValueError("Left-join cardinality failure")
    panel.to_parquet(args.processed_dir / "master_stock_day_panel.parquet", index=False)
    panel.to_csv(args.processed_dir / "master_stock_day_panel.csv", index=False)
    overall = panel.groupby("join_status", as_index=False).size().rename(columns={"size": "rows"})
    by_date = panel.groupby(["Date", "join_status"], as_index=False).size().rename(columns={"size": "rows"})
    panel["month"] = panel["Date"].dt.to_period("M").astype(str)
    by_month = panel.groupby(["month", "join_status"], as_index=False).size().rename(columns={"size": "rows"})
    by_security = panel.groupby(["canonical_research_symbol", "join_status"], as_index=False).size().rename(columns={"size": "rows"})
    overall.to_csv(args.tables_dir / "phase3_coverage_overall.csv", index=False)
    by_date.to_csv(args.tables_dir / "phase3_coverage_by_date.csv", index=False)
    by_month.to_csv(args.tables_dir / "phase3_coverage_by_month.csv", index=False)
    by_security.to_csv(args.tables_dir / "phase3_coverage_by_security.csv", index=False)
    panel.loc[panel["join_status"] != "complete_match"].head(100).to_csv(args.tables_dir / "phase3_unmatched_examples.csv", index=False)
    print(f"spine_rows={len(spine)}; panel_rows={len(panel)}; finra_candidate_rows={len(finra)}")


if __name__ == "__main__":
    raise SystemExit(main())
