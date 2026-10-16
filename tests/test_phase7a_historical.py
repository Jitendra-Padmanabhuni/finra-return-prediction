from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_phase7a_spine_universe_and_coverage_gate() -> None:
    panel = pd.read_parquet(ROOT / "data/processed/phase7a_candidate_history_panel.parquet")
    monthly = pd.read_csv(ROOT / "results/tables/phase7a_top400_monthly_audit.csv", parse_dates=["rebalance_date", "window_min", "window_max"])
    dates = pd.read_csv(ROOT / "results/tables/phase7a_shared_market_dates.csv", parse_dates=["Date"])["Date"]
    gate = json.loads((ROOT / "data/processed/phase7a_coverage_gate.json").read_text())

    assert len(panel) == 576 * 686
    assert not panel.duplicated(["Date", "canonical_research_symbol"]).any()
    assert panel.groupby("Date").size().eq(576).all()
    selected = monthly.loc[monthly.status.eq("selected")]
    assert selected["selected"].eq(400).all()
    assert selected["window_dates"].eq(20).all()
    assert (selected["window_max"] < selected["rebalance_date"]).all()
    for row in selected.itertuples(index=False):
        location = int(dates.searchsorted(row.rebalance_date))
        assert row.window_min == dates.iloc[location - 20]
        assert row.window_max == dates.iloc[location - 1]
    evaluation = panel.loc[panel.Date.between("2023-01-03", "2025-05-27") & panel.universe_member]
    assert evaluation.groupby("Date").size().eq(400).all()
    assert gate["coverage_gate_pass"] and gate["complete_market_finra_rate"] > 0.9999
    missing = ~evaluation.finra_observation_present
    assert evaluation.loc[missing, ["ShortVolume", "ShortExemptVolume", "TotalVolume"]].isna().all().all()


def test_phase7a_exact_60_history_and_shared_target_mapping() -> None:
    panel = pd.read_parquet(ROOT / "data/processed/phase7a_candidate_history_panel.parquet")
    dates = pd.Series(sorted(panel.Date.unique()))
    mapping = dict(zip(dates.iloc[:-1], dates.iloc[1:], strict=True))
    evaluation = panel.loc[panel.Date.between("2023-01-03", "2025-05-27") & panel.universe_member]
    available = evaluation.target_available
    assert evaluation.loc[available].apply(lambda row: row.designated_target_date == mapping[row.Date], axis=1).all()
    assert (evaluation.loc[available, "designated_target_date"] > evaluation.loc[available, "Date"]).all()

    sample = evaluation.loc[evaluation.S1.notna()].sort_values(["Date", "canonical_research_symbol"]).iloc[::12000].head(20)
    indexed = panel.set_index(["canonical_research_symbol", "Date"]).sort_index()
    date_locations = {date: index for index, date in enumerate(dates)}
    for row in sample.itertuples(index=False):
        location = date_locations[row.Date]
        prior_dates = dates.iloc[location - 60:location]
        history = indexed.loc[(row.canonical_research_symbol, prior_dates), "q"].to_numpy()
        assert len(history) == 60 and np.isfinite(history).all()
        median = np.median(history)
        mad = np.median(np.abs(history - median))
        assert np.isclose(row.historical_median, median)
        assert np.isclose(row.historical_mad, mad)
        expected = -(row.q - median) / (1.4826 * mad + 0.000001)
        assert np.isclose(row.S1, expected)


def test_phase7a_finra_manifest_and_original_replication() -> None:
    manifest = [json.loads(line) for line in (ROOT / "data/raw/phase7a_finra_consolidated_nms_manifest.jsonl").read_text().splitlines()]
    assert len(manifest) == 686
    assert all(row["trailer_count"] > 0 for row in manifest)
    for row in manifest[::137]:
        path = ROOT / "data/raw" / row["filename"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
    replication = pd.read_csv(ROOT / "results/tables/phase7a_original_replication_validation.csv")
    assert len(replication) == 4
    assert replication["exact_within_1e_15"].all()
