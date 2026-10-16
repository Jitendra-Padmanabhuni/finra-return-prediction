"""Build the Phase 7B all-candidate raw history panel from existing files only."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from build_master_panel import parse_candidate_finra


def finra_mapping(candidates: pd.DataFrame) -> pd.DataFrame:
    mappings = candidates[["source_symbol", "yahoo_symbol"]].rename(columns={"source_symbol": "canonical_research_symbol"})
    mappings["finra_symbol"] = mappings["canonical_research_symbol"]
    mappings.loc[mappings["canonical_research_symbol"].eq("BRK.B"), "finra_symbol"] = "BRK/B"
    mappings.loc[mappings["canonical_research_symbol"].eq("BF.B"), "finra_symbol"] = "BF/B"
    return mappings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--tables-dir", type=Path, default=Path("results/tables"))
    args = parser.parse_args()
    candidates = pd.read_csv(args.tables_dir / "phase2_candidate_universe.csv")
    market = pd.read_csv(args.processed_dir / "prototype_market_panel.csv", parse_dates=["Date"])
    membership = pd.read_csv(args.processed_dir / "prototype_universe_daily.csv", parse_dates=["Date"])
    mappings = finra_mapping(candidates)
    dates = market[["Date"]].drop_duplicates().sort_values("Date")
    spine = dates.merge(mappings, how="cross")
    if len(spine) != len(dates) * len(mappings) or spine.duplicated(["Date", "canonical_research_symbol"]).any():
        raise ValueError("Candidate-history expected spine is not one row per date/security")

    market = market.rename(columns={"source_symbol": "canonical_research_symbol", "yahoo_symbol": "market_yahoo_symbol"})
    finra = parse_candidate_finra(args.raw_dir, dates["Date"], mappings)
    finra = finra.merge(mappings[["canonical_research_symbol", "finra_symbol"]], on="finra_symbol", how="left", validate="many_to_one")
    member = membership[["Date", "source_symbol"]].rename(columns={"source_symbol": "canonical_research_symbol"}).copy()
    member["universe_member"] = True
    if member.duplicated(["Date", "canonical_research_symbol"]).any() or not member.groupby("Date").size().eq(400).all():
        raise ValueError("Corrected top-400 daily membership is invalid")

    panel = spine.merge(market, on=["Date", "canonical_research_symbol"], how="left", validate="one_to_one", indicator="market_join")
    panel = panel.merge(finra, on=["Date", "canonical_research_symbol"], how="left", validate="one_to_one", indicator="finra_join")
    panel = panel.merge(member, on=["Date", "canonical_research_symbol"], how="left", validate="one_to_one")
    panel["universe_member"] = panel["universe_member"].eq(True)
    panel["market_observation_present"] = panel["market_join"].eq("both")
    panel["finra_observation_present"] = panel["finra_join"].eq("both")
    panel["market_availability_status"] = panel["market_observation_present"].map({True: "present", False: "missing_market_observation"})
    panel["finra_availability_status"] = panel["finra_observation_present"].map({True: "present", False: "missing_finra_observation"})
    panel["symbol_mapping_status"] = "mapped"
    panel.loc[panel["canonical_research_symbol"].isin(["BRK.B", "BF.B"]), "symbol_mapping_status"] = "explicit_finra_slash_and_yahoo_hyphen_mapping"
    if panel.duplicated(["Date", "canonical_research_symbol"]).any() or len(panel) != len(spine):
        raise ValueError("Candidate-history left join changed spine cardinality")
    args.processed_dir.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(args.processed_dir / "candidate_history_panel.parquet", index=False)
    panel.to_csv(args.processed_dir / "candidate_history_panel.csv", index=False)
    coverage = panel.groupby(["universe_member", "market_availability_status", "finra_availability_status"], as_index=False).size().rename(columns={"size": "rows"})
    coverage.to_csv(args.tables_dir / "phase7b_candidate_history_coverage.csv", index=False)
    print(f"dates={len(dates)}; candidates={len(mappings)}; rows={len(panel)}; member_rows={int(panel.universe_member.sum())}")


if __name__ == "__main__":
    raise SystemExit(main())
