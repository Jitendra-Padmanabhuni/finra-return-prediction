from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from src.build_final_rank_score_phase9 import assign_bounded_rank_score


ROOT = Path(__file__).resolve().parents[1]


def test_bounded_score_formula_ties_missing_and_target_independence() -> None:
    frame = pd.DataFrame({
        "Date": pd.to_datetime(["2025-01-02"] * 4),
        "canonical_research_symbol": ["B", "A", "C", "MISSING"],
        "universe_member": [True, True, True, True],
        "S1": [0.1, 0.1, 0.2, np.nan],
        "forward_oc_return": [.9, -.9, .1, .2],
        "target_available": [True, False, True, True],
    })
    scored = assign_bounded_rank_score(frame, "S1", "final_rank_score")
    values = scored.set_index("canonical_research_symbol")
    assert values.loc["A", "S1_rank"] == 1  # alphabetical tie break
    assert values.loc["B", "S1_rank"] == 2
    assert values.loc["C", "S1_rank"] == 3
    assert np.allclose(values.loc[["A", "B", "C"], "final_rank_score"], [-1, 0, 1])
    assert np.isnan(values.loc["MISSING", "final_rank_score"])
    assert np.isclose(values["final_rank_score"].dropna().mean(), 0)
    changed_target = frame.copy(); changed_target["forward_oc_return"] = [99, 99, -99, 0]; changed_target["target_available"] = False
    rescored = assign_bounded_rank_score(changed_target, "S1", "final_rank_score")
    pd.testing.assert_series_equal(scored["final_rank_score"], rescored["final_rank_score"])


def test_singleton_score_is_centered_zero() -> None:
    frame = pd.DataFrame({"Date": pd.to_datetime(["2025-01-02"]), "canonical_research_symbol": ["ONLY"], "universe_member": [True], "S1": [2.0]})
    scored = assign_bounded_rank_score(frame, "S1", "final_rank_score")
    assert scored.loc[0, "S1_rank"] == 1
    assert scored.loc[0, "S1_rank_n"] == 1
    assert scored.loc[0, "final_rank_score"] == 0


def test_phase9_artifact_bounds_centering_and_prior_preservation() -> None:
    panel = pd.read_parquet(ROOT / "data/processed/phase9_final_rank_score_panel.parquet")
    assert panel.groupby("sample")["Date"].nunique().to_dict() == {
        "additional_2023-01-03_2025-05-27": 601,
        "original_2025-05-28_2026-08-31": 317,
    }
    assert panel.groupby(["sample", "Date"]).size().eq(400).all()
    assert panel["universe_member"].all()
    for score in ["S0_bounded_rank_score", "final_rank_score", "S2_bounded_rank_score"]:
        valid = panel[score].dropna()
        assert valid.between(-1, 1).all()
        daily = panel.loc[panel[score].notna()].groupby(["sample", "Date"])[score].agg(["mean", "min", "max", "size"])
        assert np.allclose(daily["mean"], 0, atol=1e-12, rtol=0)
        multi = daily["size"] >= 2
        assert np.allclose(daily.loc[multi, "min"], -1, atol=1e-12)
        assert np.allclose(daily.loc[multi, "max"], 1, atol=1e-12)
    equivalence = pd.read_csv(ROOT / "results/tables/phase9_s1_rank_ic_equivalence.csv")
    assert np.allclose(equivalence["difference"], 0, atol=1e-12, rtol=0)
    for line in (ROOT / "preservation/phase9_pre_score_source_artifacts/SHA256SUMS.txt").read_text().splitlines():
        digest, relative = line.split("  ", 1)
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest
