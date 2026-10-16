from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from one_sided_ic_inference import (  # noqa: E402
    ONE_SIDED_IC_CRITICAL_VALUE,
    TWO_SIDED_IC_CRITICAL_VALUE_SUPERSEDED,
    ic_clears_one_sided_bar,
    ic_clears_two_sided_bar_superseded,
)


def test_phase8_s2_cell_and_common_sample_invariants() -> None:
    formation = pd.read_parquet(ROOT / "data/processed/phase8_s2_formation_panel.parquet")
    common = pd.read_parquet(ROOT / "data/processed/phase8_common_evaluation_panel.parquet")
    coverage = pd.read_csv(ROOT / "results/tables/phase8_common_sample_coverage.csv")
    assert not formation.duplicated(["sample", "Date", "canonical_research_symbol"]).any()
    assert not common.duplicated(["sample", "Date", "canonical_research_symbol"]).any()
    assert not {"forward_oc_return", "target_available"}.intersection(formation.columns)
    assert formation[["vs_bucket", "vol_bucket", "state_cell"]].notna().all().all()
    assert formation["vs_bucket"].between(1, 5).all()
    assert formation["vol_bucket"].between(1, 5).all()
    assert formation["state_cell"].between(1, 25).all()
    assert formation.groupby(["sample", "Date", "canonical_research_symbol"]).size().eq(1).all()
    assert np.allclose(formation.groupby(["sample", "Date", "state_cell"])["a"].median(), 0, atol=1e-12, rtol=0)
    assert (formation.groupby(["sample", "Date", "state_cell"])["cell_size"].first() >= 1).all()
    assert common[["S0", "S1", "S2", "forward_oc_return"]].notna().all().all()
    assert coverage["s2_common_retained_from_s1"].eq(1.0).all()


def test_one_sided_ic_bar_constants_and_helper() -> None:
    """Amended 2026-09-12: one-sided primary rule (t >= 1.645) for Rank-IC and
    paired IC-difference tests, replacing the prior two-sided |t| >= 2 rule."""
    assert ONE_SIDED_IC_CRITICAL_VALUE == 1.645
    assert TWO_SIDED_IC_CRITICAL_VALUE_SUPERSEDED == 2.0
    # Exactly at the new bar: pass.
    assert ic_clears_one_sided_bar(1.645) is True
    # Just below the new bar: fail.
    assert ic_clears_one_sided_bar(1.6449) is False
    # The specific historical flip: t=1.83 (original-period standalone S0 IC)
    # failed the old two-sided bar but clears the new one-sided bar.
    assert ic_clears_two_sided_bar_superseded(1.83) is False
    assert ic_clears_one_sided_bar(1.83) is True
    # t=1.90 (Phase 5 / Phase 6 / Phase 7B full-sample S0 IC) also flips.
    assert ic_clears_two_sided_bar_superseded(1.8997) is False
    assert ic_clears_one_sided_bar(1.8997) is True
    # t=1.74 (Phase 7 member-history paired S0 IC) also flips.
    assert ic_clears_two_sided_bar_superseded(1.7373) is False
    assert ic_clears_one_sided_bar(1.7373) is True
    # The closest paired IC-difference case (additional S2-minus-S1, t=1.5627)
    # must still fail under the new bar.
    assert ic_clears_one_sided_bar(1.562703) is False
    # A negative t must fail regardless of magnitude (one-sided, not |t|).
    assert ic_clears_one_sided_bar(-2.5) is False
    assert ic_clears_two_sided_bar_superseded(-2.5) is True
    # Values that already passed the old two-sided bar still pass the new one.
    for already_passing_t in [2.24, 2.51, 2.59, 2.73, 3.48]:
        assert ic_clears_two_sided_bar_superseded(already_passing_t) is True
        assert ic_clears_one_sided_bar(already_passing_t) is True


def test_phase8_decision_json_reflects_one_sided_amendment() -> None:
    """The dedicated 2026-09-12 amendment JSON must use the one-sided bar as
    primary and preserve the superseded two-sided value for audit, without
    changing the unchanged underlying S2 HAC(5) IC t-statistics. It must be a
    separate file from the original `phase8_decision_rule_evaluation.json`,
    whose checksum is pinned in the Phase 9/10/11 preservation manifests and
    must not change."""
    original_path = ROOT / "results/tables/phase8_decision_rule_evaluation.json"
    amended_path = ROOT / "results/tables/phase8_decision_rule_evaluation_one_sided_amendment_2026-09-12.json"
    decision = json.loads(amended_path.read_text())
    original = json.loads(original_path.read_text())
    summary = pd.read_csv(ROOT / "results/tables/phase8_common_sample_performance.csv")
    for sample, entry in decision.items():
        s2_t = summary.query("sample == @sample and signal == 'S2'").iloc[0].hac5_ic_t
        assert entry["one_sided_ic_critical_value"] == ONE_SIDED_IC_CRITICAL_VALUE
        assert entry["s2_hac5_ic_t_at_least_1_645_one_sided_primary"] == ic_clears_one_sided_bar(s2_t)
        assert entry["s2_hac5_ic_t_at_least_2_two_sided_superseded"] == ic_clears_two_sided_bar_superseded(s2_t)
        # The independent, non-threshold conditions must be unchanged from the
        # original frozen result.
        assert entry["s2_minus_s1_ic_positive"] == original[sample]["s2_minus_s1_ic_positive"]
        assert entry["small_cell_fraction"] == pytest.approx(original[sample]["small_cell_fraction"], abs=1e-9)
    # Both samples' S2 already cleared the old two-sided bar, so the primary
    # criterion switch does not by itself change the leading-candidate result;
    # the original sample stays blocked by the independent sign requirement.
    assert decision["additional_2023-01-03_2025-05-27"]["s2_minus_s1_ic_positive"] is True
    assert decision["original_2025-05-28_2026-08-31"]["s2_minus_s1_ic_positive"] is False
    # The originally pinned file must be byte-for-byte unchanged (checked
    # against the Phase 9/10/11 preservation manifests elsewhere); confirm its
    # own decisive field still reflects the original two-sided rule's key name.
    assert original["original_2025-05-28_2026-08-31"]["s2_hac5_t_at_least_2"] is True


def test_one_sided_amendment_did_not_disturb_pinned_decision_file() -> None:
    """`phase8_decision_rule_evaluation.json` is pinned as a frozen source
    artifact in the Phase 9, 10, and 11 preservation manifests. The one-sided
    IC amendment must apply non-destructively via a separate output file, so
    this file's checksum must still match what those manifests recorded."""
    original_path = ROOT / "results/tables/phase8_decision_rule_evaluation.json"
    digest = hashlib.sha256(original_path.read_bytes()).hexdigest()
    manifests = [
        ROOT / "preservation/phase9_pre_score_source_artifacts/SHA256SUMS.txt",
        ROOT / "preservation/phase10_pre_backtest_source_artifacts/SHA256SUMS.txt",
        ROOT / "preservation/phase11_pre_robustness_source_artifacts/SHA256SUMS.txt",
    ]
    checked = 0
    for manifest in manifests:
        for line in manifest.read_text().splitlines():
            pinned_digest, relative = line.split("  ", 1)
            if relative == "results/tables/phase8_decision_rule_evaluation.json":
                assert pinned_digest == digest
                checked += 1
    assert checked == len(manifests)


def test_phase8_rolling_inputs_are_strictly_prior() -> None:
    formation = pd.read_parquet(ROOT / "data/processed/phase8_s2_formation_panel.parquet")
    source = pd.read_parquet(ROOT / "data/processed/phase7a_candidate_history_panel.parquet")
    additional = formation.loc[formation["sample"].str.startswith("additional")].sort_values(["Date", "canonical_research_symbol"]).iloc[::15000].head(12)
    dates = pd.Series(sorted(source.Date.unique()))
    positions = {date: i for i, date in enumerate(dates)}
    for row in additional.itertuples(index=False):
        prior = dates.iloc[positions[row.Date] - 20:positions[row.Date]]
        history = source.loc[
            source["canonical_research_symbol"].eq(row.canonical_research_symbol)
            & source["Date"].isin(prior)
        ].sort_values("Date")
        assert len(history) == 20
        assert history["Volume"].notna().all() and history["Volume"].gt(0).all()
        assert np.isclose(row.prior_volume_median_20, history["Volume"].median())
        assert row.Date not in prior.to_list()
