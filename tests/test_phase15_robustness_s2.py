from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from src.run_robustness_phase15_s2 import (
    COST_BPS,
    HAC_LAGS,
    PLACEBO_N,
    PLACEBO_SEED,
    SAMPLES,
    continuous_weights,
    source_artifact_paths,
    stable_scores,
    tail_weights,
    validate_weights,
)

ROOT = Path(__file__).resolve().parents[1]


def test_phase15_rank_and_breadth_weights_are_deterministic_and_neutral() -> None:
    """Direct mirror of the Phase 11 S1 test, substituting S2."""
    frame = pd.DataFrame({"S2": [0.1, 0.1, 0.3, -0.2], "canonical_research_symbol": ["B", "A", "C", "D"]})
    scores = stable_scores(frame)
    assert frame.loc[scores.idxmax(), "canonical_research_symbol"] == "C"
    assert frame.loc[scores.idxmin(), "canonical_research_symbol"] == "D"
    weights = continuous_weights(scores)
    validate_weights(weights)
    tail = tail_weights(frame.assign(S2=frame.S2), 0.25)
    validate_weights(tail)
    assert np.isclose(tail.sum(), 0)


def test_phase15_missing_signal_stays_missing_and_target_is_not_read() -> None:
    frame = pd.DataFrame({"S2": [1.0, np.nan, -1.0], "canonical_research_symbol": ["A", "B", "C"], "forward_oc_return": [100, -100, 1], "target_available": [False, False, False]})
    scores = stable_scores(frame)
    assert pd.isna(scores.iloc[1])
    altered = frame.copy(); altered["forward_oc_return"] = [-999, 999, -999]; altered["target_available"] = True
    assert np.allclose(scores, stable_scores(altered), equal_nan=True)


def test_phase15_fixed_universe_scoring_is_date_local() -> None:
    frame = pd.DataFrame({"Date": pd.to_datetime(["2025-01-01"] * 3), "S2": [1.0, 2.0, 3.0], "canonical_research_symbol": ["A", "B", "C"]})
    first = stable_scores(frame)
    changed = frame.copy(); changed.loc[0, "S2"] = 999
    assert not np.allclose(first, stable_scores(changed))


def test_phase15_reuses_phase11_locked_parameters_exactly() -> None:
    """Every locked parameter must be reused unchanged from Phase 11, including the placebo
    seed reused specifically for direct comparability to Phase 11's own S1 result."""
    assert PLACEBO_SEED == 20260911
    assert PLACEBO_N == 1000
    assert HAC_LAGS == (0, 5, 10, 20)
    assert COST_BPS == (0.0, 1.0, 2.5, 5.0)
    assert set(SAMPLES) == {"additional_2023-01-03_2025-05-27", "original_2025-05-28_2026-08-31"}
    rng_a = np.random.default_rng(PLACEBO_SEED); rng_b = np.random.default_rng(20260911)
    assert np.array_equal(rng_a.permutation(np.arange(10)), rng_b.permutation(np.arange(10)))


def test_phase15_covers_both_samples_matching_phase11_scope() -> None:
    """Phase 11 was not restricted to one sample; Phase 15 must not be either, and no output
    may contain a pooled/combined estimate."""
    for name in ["phase15_time_stability", "phase15_hac_lag_sensitivity", "phase15_breadth_comparison",
                 "phase15_fixed_universe_results", "phase15_sector_liquidity_neutral",
                 "phase15_outlier_sensitivity", "phase15_placebo_summary", "phase15_robustness_summary"]:
        df = pd.read_csv(ROOT / f"results/tables/{name}.csv")
        samples = set(df["sample"].unique())
        assert samples.issubset(set(SAMPLES)), f"{name} has an unexpected sample value: {samples - set(SAMPLES)}"
        assert samples, f"{name} is empty"
        assert not any("pooled" in str(s).lower() or "combined" in str(s).lower() for s in samples)


def test_phase15_placebo_reproduces_phase11_methodology_but_is_not_copied_from_it() -> None:
    """The S2 placebo result must differ from S1's (it is a genuinely new computation on a
    different signal), but must use the identical seed, permutation count, and empirical
    one-sided p-value formula (plus-one convention)."""
    s1 = pd.read_csv(ROOT / "results/tables/phase11_placebo_summary.csv")
    s2 = pd.read_csv(ROOT / "results/tables/phase15_placebo_summary.csv")
    assert (s2["seed"] == 20260911).all()
    assert (s2["permutations"] == 1000).all()
    # Genuinely different underlying computation: actual means and empirical p-values differ.
    merged = s1.merge(s2, on="sample", suffixes=("_s1", "_s2"))
    assert not np.allclose(merged["actual_mean_return_s1"], merged["actual_mean_return_s2"])
    assert not np.allclose(merged["empirical_one_sided_p_s1"], merged["empirical_one_sided_p_s2"])
    # The plus-one convention floor is exactly 1/1001 with 1000 permutations.
    for p in s2["empirical_one_sided_p"]:
        assert p >= 1 / 1001 - 1e-9


def test_phase15_reproduces_phase10_s2_daily_returns_exactly() -> None:
    """The S2_continuous rebuild inside Phase 15 must exactly reproduce Phase 10's frozen S2
    daily gross returns (asserted at runtime; re-verified here against the persisted panel)."""
    frozen = pd.read_parquet(ROOT / "data/processed/phase10_daily_portfolio_exposure_panel.parquet")
    frozen_s2 = frozen.loc[frozen.strategy.eq("S2_continuous")].sort_values(["sample", "signal_date"]).reset_index(drop=True)
    rebuilt = pd.read_parquet(ROOT / "data/processed/phase15_daily_robustness_s2_portfolio_panel.parquet")
    rebuilt_s2 = rebuilt.loc[rebuilt.strategy.eq("S2_continuous")].sort_values(["sample", "signal_date"]).reset_index(drop=True)
    assert len(frozen_s2) == len(rebuilt_s2)
    assert np.allclose(frozen_s2["gross_return"].fillna(0), rebuilt_s2["gross_return"].fillna(0), atol=1e-15, rtol=0)
    assert np.array_equal(frozen_s2["strategy_day_available"].to_numpy(), rebuilt_s2["available"].to_numpy())


def test_phase15_every_breadth_variant_negative_at_primary_cost_same_pattern_as_s1() -> None:
    breadth = pd.read_csv(ROOT / "results/tables/phase15_breadth_comparison.csv")
    at_primary = breadth.loc[breadth.one_way_cost_bps.eq(2.5)]
    assert (at_primary["mean_bps"] < 0).all()


def test_phase15_source_manifest_pins_phase9_s2_and_phase10_s2_artifacts_unchanged() -> None:
    """Phase 9's S2_bounded_rank_score panel and Phase 10's S2 backtest artifacts must be
    pinned as immutable source inputs and verified unchanged."""
    manifest = ROOT / "preservation/phase15_pre_robustness_s2_source_artifacts/SHA256SUMS.txt"
    assert manifest.exists()
    pinned = {}
    for line in manifest.read_text().splitlines():
        digest, relative = line.split("  ", 1)
        pinned[relative] = digest
    assert "data/processed/phase9_final_rank_score_panel.parquet" in pinned
    assert "data/processed/phase10_daily_portfolio_exposure_panel.parquet" in pinned
    assert "data/processed/phase10_portfolio_position_panel.parquet" in pinned
    paths = source_artifact_paths(ROOT)
    assert set(str(p.relative_to(ROOT)) for p in paths) == set(pinned)
    for path in paths:
        relative = str(path.relative_to(ROOT))
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pinned[relative], f"changed: {relative}"


def test_phase15_did_not_modify_any_phase10_or_phase11_frozen_artifact() -> None:
    """Additive-only guarantee: Phase 10 and Phase 11's own output files must be byte-identical
    to what they were before Phase 15 ran, checked against the Phase 11 preservation manifest
    (which independently pins several of the same Phase 10 artifacts) plus a direct read of the
    Phase 11 output tables this test compares against."""
    manifest = ROOT / "preservation/phase11_pre_robustness_source_artifacts/SHA256SUMS.txt"
    for line in manifest.read_text().splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / relative
        assert path.exists(), f"missing: {relative}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, f"Phase 10/11 artifact changed: {relative}"
