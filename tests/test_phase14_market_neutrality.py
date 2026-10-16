from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats

from src.run_market_neutrality_phase14 import (
    ALPHA_CRITICAL_VALUE,
    HAC_LAGS,
    ORIGINAL_SAMPLE,
    STRATEGIES,
    build_market_factor,
    coverage_check,
    load_strategy_returns,
    market_model_stats,
    source_artifact_paths,
)

ROOT = Path(__file__).resolve().parents[1]


def test_hac_lag_matches_project_convention() -> None:
    """This phase must use the same HAC(5) machinery as every other phase."""
    assert HAC_LAGS == 5
    assert ALPHA_CRITICAL_VALUE == 1.645


def test_market_model_stats_matches_manual_statsmodels_fit() -> None:
    """The regression helper must reproduce a hand-built OLS+HAC(5) fit exactly."""
    rng = np.random.default_rng(20260912)
    market = pd.Series(rng.normal(0, 0.01, 250))
    strategy = pd.Series(0.0002 + 0.3 * market + rng.normal(0, 0.002, 250))

    result = market_model_stats(strategy, market)

    x = sm.add_constant(market.to_numpy())
    fit = sm.OLS(strategy.to_numpy(), x).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    assert result["alpha"] == pytest.approx(float(fit.params[0]))
    assert result["beta"] == pytest.approx(float(fit.params[1]))
    assert result["alpha_hac5_se"] == pytest.approx(float(fit.bse[0]))
    assert result["beta_hac5_se"] == pytest.approx(float(fit.bse[1]))
    assert result["alpha_hac5_t"] == pytest.approx(float(fit.tvalues[0]))
    assert result["beta_hac5_t"] == pytest.approx(float(fit.tvalues[1]))
    assert result["n"] == 250


def test_alpha_is_one_sided_beta_is_two_sided() -> None:
    """Alpha must use the one-sided H0: alpha<=0 p-value; beta the two-sided H0: beta=0 p-value."""
    market = pd.Series([0.001, -0.002, 0.003, -0.001, 0.002] * 40)
    # A strategy with a clearly positive, HAC-significant intercept and near-zero beta.
    rng = np.random.default_rng(1)
    strategy = pd.Series(0.001 + 0.0 * market + rng.normal(0, 0.0001, len(market)))
    result = market_model_stats(strategy, market)

    assert result["alpha_one_sided_p_greater_zero"] == pytest.approx(float(stats.norm.sf(result["alpha_hac5_t"])))
    assert result["beta_two_sided_p"] == pytest.approx(float(2 * stats.norm.sf(abs(result["beta_hac5_t"]))))
    # A large positive t should give a small one-sided p and pass the primary bar.
    assert result["alpha_hac5_t"] > ALPHA_CRITICAL_VALUE
    assert result["alpha_clears_primary_bar_1_645"] is True
    assert result["alpha_one_sided_p_greater_zero"] < 0.05

    # Alpha's decision rule must be one-sided (t >= critical value), not |t| >= critical value:
    # a large-magnitude NEGATIVE alpha t must still fail the primary bar.
    negative_strategy = pd.Series(-0.001 + rng.normal(0, 0.0001, len(market)))
    negative_result = market_model_stats(negative_strategy, market)
    assert negative_result["alpha_hac5_t"] < -ALPHA_CRITICAL_VALUE
    assert negative_result["alpha_clears_primary_bar_1_645"] is False


def test_beta_flag_uses_two_sided_significance_and_magnitude() -> None:
    """The beta diagnostic flag must trigger on |beta| or two-sided significance, not one-sided sign."""
    market = pd.Series(np.linspace(-0.02, 0.02, 200))
    rng = np.random.default_rng(2)
    # A strongly negative but large-magnitude beta must still be flagged (diagnostic is symmetric).
    strategy = pd.Series(-0.5 * market + rng.normal(0, 0.0005, 200))
    result = market_model_stats(strategy, market)
    assert result["beta"] < -0.10
    assert result["beta_flag_large_or_significant"] is True


def test_date_alignment_is_per_strategy_and_excludes_unavailable_days() -> None:
    """Loaded original-sample strategy returns must come only from the frozen Phase 10 panels,
    only the original sample, and only Phase-10-available strategy-days (no zero-fill, no
    rebuild)."""
    strategy_returns = load_strategy_returns(ROOT)
    assert set(strategy_returns["strategy"].unique()) == set(STRATEGIES)
    # No trade date outside the locked original-sample evaluation window.
    assert strategy_returns["trade_date"].min() >= pd.Timestamp("2025-05-28")
    assert strategy_returns["trade_date"].max() <= pd.Timestamp("2026-09-02")
    counts = strategy_returns.groupby("strategy").size()
    # S0 has exactly one fewer available day than S1/S2 (the known FISV missing-target day),
    # reproducing Phase 10's own HAC test construction (316 of 317 days).
    assert counts["S0_continuous"] == 316
    assert counts["S1_continuous"] == 317
    assert counts["S2_continuous"] == 317
    # No duplicate (strategy, trade_date) rows.
    assert not strategy_returns.duplicated(["strategy", "trade_date"]).any()


def test_market_factor_formula_matches_project_convention() -> None:
    """adjusted_open = Open * (Adj Close / Close); market_return = adjusted_close/adjusted_open - 1,
    matching build_prediction_target.py's / build_historical_panel_phase7a.py's construction."""
    raw = pd.DataFrame({
        "Date": pd.to_datetime(["2026-01-02", "2026-01-05"]),
        "Open": [100.0, 102.0],
        "Close": [101.0, 100.0],
        "Adj Close": [99.5, 98.0],
    })
    factor = build_market_factor(raw)
    expected_adj_open_0 = 100.0 * (99.5 / 101.0)
    assert factor.loc[0, "adjusted_open"] == pytest.approx(expected_adj_open_0)
    assert factor.loc[0, "adjusted_close"] == pytest.approx(99.5)
    assert factor.loc[0, "market_return"] == pytest.approx(99.5 / expected_adj_open_0 - 1)


def test_coverage_check_reports_missing_dates_per_strategy() -> None:
    strategy_returns = pd.DataFrame({
        "strategy": ["S0_continuous", "S0_continuous", "S1_continuous"],
        "trade_date": pd.to_datetime(["2026-01-02", "2026-01-05", "2026-01-02"]),
    })
    market_factor = pd.DataFrame({"trade_date": pd.to_datetime(["2026-01-02"]), "market_return": [0.001]})
    result = coverage_check(strategy_returns, market_factor)
    s0 = result.loc[result.strategy == "S0_continuous"].iloc[0]
    s1 = result.loc[result.strategy == "S1_continuous"].iloc[0]
    assert s0.missing_from_spy == 1
    assert "2026-01-05" in s0.missing_dates
    assert s1.missing_from_spy == 0


def test_scope_excludes_additional_sample() -> None:
    assert ORIGINAL_SAMPLE == "original_2025-05-28_2026-08-31"
    strategy_returns = load_strategy_returns(ROOT)
    # The loader must never touch the additional sample; there is no "sample" column left to
    # accidentally include it, and every trade date must fall within the original window.
    assert "sample" not in strategy_returns.columns
    assert strategy_returns["trade_date"].between("2025-05-28", "2026-09-02").all()


def test_phase14_does_not_modify_any_phase_10_frozen_artifact() -> None:
    """Re-running source-artifact hashing must reproduce the pinned manifest exactly."""
    manifest = ROOT / "preservation/phase14_pre_market_neutrality_source_artifacts/SHA256SUMS.txt"
    assert manifest.exists()
    paths = source_artifact_paths(ROOT)
    pinned = {}
    for line in manifest.read_text().splitlines():
        digest, relative = line.split("  ", 1)
        pinned[relative] = digest
    assert set(str(p.relative_to(ROOT)) for p in paths) == set(pinned)
    for path in paths:
        relative = str(path.relative_to(ROOT))
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == pinned[relative], f"Phase 10 source artifact changed: {relative}"


def test_alpha_estimates_track_raw_phase10_gross_means() -> None:
    """Sanity cross-check: each strategy's regression alpha should sit close to its own raw
    Phase 10 original-sample gross mean (computed independently here from the frozen exposure
    panel), with the gap explained by beta * mean(market_return)."""
    exposure = pd.read_parquet(ROOT / "data/processed/phase10_daily_portfolio_exposure_panel.parquet")
    results = pd.read_csv(ROOT / "results/tables/phase14_market_model_results.csv")
    for strategy in STRATEGIES:
        raw_mean = exposure.loc[
            (exposure["sample"] == ORIGINAL_SAMPLE) & (exposure["strategy"] == strategy) & exposure["strategy_day_available"]
        ]["gross_return"].mean()
        alpha = results.loc[(results.strategy == strategy) & (results.return_type == "gross"), "alpha"].iloc[0]
        # Alpha and the raw mean must be close (within 5 bps/day) for a strategy with small beta
        # against a factor whose own mean is small; this is a sanity bound, not an exact identity.
        assert abs(alpha - raw_mean) < 0.0005


def test_phase14_outputs_exist_and_cover_all_three_strategies() -> None:
    results = pd.read_csv(ROOT / "results/tables/phase14_market_model_results.csv")
    assert set(results["strategy"].unique()) == set(STRATEGIES)
    assert set(results["return_type"].unique()) == {"gross", "net"}
    # Every row must carry both the one-sided alpha p-value and the two-sided beta p-value.
    assert results["alpha_one_sided_p_greater_zero"].notna().all()
    assert results["beta_two_sided_p"].notna().all()
    coverage = pd.read_csv(ROOT / "results/tables/phase14_spy_coverage_check.csv")
    assert (coverage["missing_from_spy"] == 0).all()
