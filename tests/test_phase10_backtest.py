from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from src.run_realistic_backtest_phase10 import add_cost_returns, continuous_weights, form_strategy_days, s1_decile_weights, validate_weight_vector


ROOT = Path(__file__).resolve().parents[1]


def toy_day() -> pd.DataFrame:
    return pd.DataFrame({
        "sample": ["sample"] * 3,
        "Date": pd.to_datetime(["2025-01-02"] * 3),
        "canonical_research_symbol": ["A", "B", "C"],
        "S0": [-.2, -.3, -.4], "S1": [-1.0, 0.0, 1.0], "S2": [-1.0, 0.0, 1.0],
        "final_rank_score": [-1.0, 0.0, 1.0], "S0_bounded_rank_score": [-1.0, 0.0, 1.0], "S2_bounded_rank_score": [-1.0, 0.0, 1.0],
        "forward_oc_return": [-.01, .02, .03], "target_available": [True, True, True],
        "designated_target_date": pd.to_datetime(["2025-01-03"] * 3),
        "prior_median_dollar_volume_20": [1e8, 1e8, 1e8],
    })


def test_continuous_weight_formula_and_exposure() -> None:
    day = toy_day()
    weights = continuous_weights(day, "final_rank_score")
    assert np.allclose(weights, [-.5, 0, .5])
    validate_weight_vector(weights, "toy")
    # Altering target columns cannot alter target-independent weight formation.
    changed = day.copy(); changed["forward_oc_return"] = [99, -99, 2]; changed["target_available"] = False
    assert np.allclose(weights, continuous_weights(changed, "final_rank_score"), equal_nan=True)


def test_costs_apply_entry_and_exit_and_return_arithmetic() -> None:
    day = toy_day()
    daily, _ = form_strategy_days(day, "S1_continuous", "final_rank_score")
    assert np.isclose(daily.loc[0, "gross_return"], .02)  # -.5×-.01 + .5×.03
    costs = add_cost_returns(daily)
    primary = costs.loc[costs.one_way_cost_bps.eq(2.5)].iloc[0]
    assert np.isclose(primary.round_trip_cost, .0005)
    assert np.isclose(primary.net_return, .0195)


def test_missing_target_marks_whole_day_unavailable_without_reweighting() -> None:
    day = toy_day(); day.loc[2, "target_available"] = False; day.loc[2, "forward_oc_return"] = np.nan
    daily, positions = form_strategy_days(day, "S1_continuous", "final_rank_score")
    assert not daily.loc[0, "strategy_day_available"]
    assert daily.loc[0, "unavailable_reason"] == "nonzero_weight_missing_designated_target"
    assert pd.isna(daily.loc[0, "gross_return"])
    assert positions.loc[positions.canonical_research_symbol.eq("C"), "weight"].iloc[0] == .5


def test_decile_weights_and_paired_dates_are_deterministic() -> None:
    day = pd.concat([toy_day()] * 4, ignore_index=True).iloc[:10].copy()
    day["canonical_research_symbol"] = [f"S{i:02d}" for i in range(10)]
    day["S1"] = np.arange(10, dtype=float)
    weights = s1_decile_weights(day)
    validate_weight_vector(weights, "decile")
    assert weights.iloc[0] == -.5
    assert weights.iloc[-1] == .5
    assert np.allclose(weights.iloc[1:-1], 0)
    panel = pd.read_parquet(ROOT / "data/processed/phase9_final_rank_score_panel.parquet")
    assert panel.groupby(["sample", "Date"]).size().eq(400).all()
    # Phase 10's immutable input is itself protected by its predecessor manifest.
    for line in (ROOT / "preservation/phase9_pre_score_source_artifacts/SHA256SUMS.txt").read_text().splitlines():
        digest, relative = line.split("  ", 1)
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest
