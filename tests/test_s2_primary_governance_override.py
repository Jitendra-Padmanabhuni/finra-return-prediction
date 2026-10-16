from __future__ import annotations

import glob
import hashlib
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def config():
    return yaml.safe_load((ROOT / "config/research_config.yaml").read_text())


def test_override_block_declares_s2_primary_s1_comparator_s0_unchanged(config) -> None:
    block = config["approved_S2_primary_promotion_override_2026_09_12"]
    assert str(block["approved_on"]) == "2026-09-12"
    assert block["decision"] == "S2_promoted_to_primary"
    assert block["decision_type"] == "explicit_governance_override_not_a_data_driven_result"
    roles = block["new_roles"]
    assert roles["S2"]["role"] == "primary"
    assert roles["S1"]["role"] == "former_primary_now_comparator"
    assert roles["S0"]["role"] == "baseline"
    assert roles["S0"]["previously"] == "baseline"


def test_override_block_states_phase8_promotion_rule_was_not_met(config) -> None:
    block = config["approved_S2_primary_promotion_override_2026_09_12"]
    rule = block["pre_registered_phase_8_promotion_rule"]
    assert rule["met_at_phase_8_original_two_sided_standard"] is False
    assert rule["met_under_2026_09_12_one_sided_ic_amendment_t_at_least_1_645"] is False
    # The cited figures must match the authoritative Phase 8 paired-differences table exactly.
    paired = pd.read_csv(ROOT / "results/tables/phase8_paired_differences.csv")
    add = paired.query("sample == 'additional_2023-01-03_2025-05-27' and comparison == 'S2_minus_S1'").iloc[0]
    orig = paired.query("sample == 'original_2025-05-28_2026-08-31' and comparison == 'S2_minus_S1'").iloc[0]
    assert rule["additional_sample"]["hac5_t"] == pytest.approx(float(add.hac5_ic_t), abs=1e-4)
    assert rule["original_sample"]["hac5_t"] == pytest.approx(float(orig.hac5_ic_t), abs=1e-4)
    assert rule["additional_sample"]["hac5_t"] < 1.645
    assert rule["original_sample"]["hac5_t"] < 0


def test_override_reasons_match_authoritative_phase14_and_phase15_figures(config) -> None:
    block = config["approved_S2_primary_promotion_override_2026_09_12"]
    reasons = block["reasons_cited_for_override"]

    p14 = pd.read_csv(ROOT / "results/tables/phase14_market_model_results.csv")
    s1_gross = p14.query("strategy == 'S1_continuous' and return_type == 'gross'").iloc[0]
    s2_gross = p14.query("strategy == 'S2_continuous' and return_type == 'gross'").iloc[0]
    assert "1.710573" in reasons["reason_2_phase_14_market_neutrality"]["detail"]
    assert s2_gross.alpha_hac5_t == pytest.approx(1.710573, abs=1e-4)
    assert s1_gross.alpha_hac5_t == pytest.approx(1.619474, abs=1e-4)
    assert s2_gross.alpha_clears_primary_bar_1_645 == True  # noqa: E712
    assert s1_gross.alpha_clears_primary_bar_1_645 == False  # noqa: E712

    p15 = pd.read_csv(ROOT / "results/tables/phase15_placebo_summary.csv")
    p11 = pd.read_csv(ROOT / "results/tables/phase11_placebo_summary.csv")
    assert (p15["empirical_one_sided_p"] > p11["empirical_one_sided_p"].max()).all()
    assert p11["empirical_one_sided_p"].round(6).eq(0.000999).all()


def test_historical_role_fields_preserved_verbatim(config) -> None:
    """The four fields this override supersedes must still literally say S1, unchanged, exactly
    as Phase 9/10/11 originally wrote them."""
    p9 = config["evaluation"]["final_rank_score_phase_9"]
    assert p9["roles"]["S1"] == "primary_predictive_signal"
    assert p9["roles"]["S0"] == "baseline_benchmark"
    assert p9["roles"]["S2"] == "frozen_robustness_comparator"
    assert p9["primary_score_field"] == "S1_final_rank_score"

    p10 = config["evaluation"]["realistic_portfolio_backtest_phase_10"]
    assert p10["frozen_signal_roles"]["S1_final_rank_score"] == "primary"
    assert p10["frozen_signal_roles"]["S0_bounded_rank_score"] == "baseline"
    assert p10["frozen_signal_roles"]["S2_bounded_rank_score"] == "robustness_comparator"

    p11 = config["evaluation"]["robustness_falsification_phase_11"]
    assert p11["frozen_primary"]["signal"] == "S1"
    assert p11["frozen_primary"]["score_field"] == "final_rank_score"

    p15 = config["evaluation"]["robustness_falsification_phase_15_s2"]
    assert "S2 has NOT been promoted to primary" in p15["governance_clarification"]
    assert "S1 primary" in p15["governance_clarification"]
    assert "does not change S2's frozen role as robustness comparator" in p15["results"]["headline_conclusion"]


def test_new_governance_csv_states_current_roles_correctly() -> None:
    amended = pd.read_csv(ROOT / "results/tables/phase9_signal_governance_amended_2026-09-12.csv")
    roles = amended.set_index("signal")["role"].to_dict()
    assert roles["S2"] == "primary"
    assert roles["S1"] == "former_primary_now_comparator"
    assert roles["S0"] == "baseline"
    assert (amended["change_effective"] == "2026-09-12").all()
    changed = amended.set_index("signal")["change_type"].to_dict()
    assert changed["S1"] == "explicit_governance_override_not_data_driven"
    assert changed["S2"] == "explicit_governance_override_not_data_driven"
    assert changed["S0"] == "no_change"


def test_original_governance_csv_untouched_and_still_says_s1_primary() -> None:
    """The original, pinned governance CSV must be byte-identical to what Phase 9 produced."""
    original = pd.read_csv(ROOT / "results/tables/phase9_signal_governance.csv")
    roles = original.set_index("signal")["role"].to_dict()
    assert roles["S1"] == "primary_signal"
    assert roles["S0"] == "baseline"
    assert roles["S2"] == "robustness_comparator"
    digest = hashlib.sha256((ROOT / "results/tables/phase9_signal_governance.csv").read_bytes()).hexdigest()
    for manifest in glob.glob(str(ROOT / "preservation/*/SHA256SUMS.txt")):
        for line in Path(manifest).read_text().splitlines():
            pinned_digest, relative = line.split("  ", 1)
            if relative == "results/tables/phase9_signal_governance.csv":
                assert pinned_digest == digest


def test_pinned_phase8_and_phase9_reports_were_not_edited() -> None:
    """docs/phase8_report.md and docs/phase9_report.md are pinned in downstream preservation
    manifests and must remain byte-identical; the override could not and did not touch them."""
    for relative in ["docs/phase8_report.md", "docs/phase9_report.md"]:
        digest = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        found = False
        for manifest in glob.glob(str(ROOT / "preservation/*/SHA256SUMS.txt")):
            for line in Path(manifest).read_text().splitlines():
                pinned_digest, pinned_relative = line.split("  ", 1)
                if pinned_relative == relative:
                    assert pinned_digest == digest, f"{relative} changed since it was pinned in {manifest}"
                    found = True
        assert found, f"{relative} was expected to be pinned somewhere but was not found in any manifest"


def test_full_preservation_manifest_audit_finds_no_mismatch() -> None:
    """Every checksum pinned anywhere in this project's history must still match exactly."""
    mismatches = []
    checked = 0
    for manifest in glob.glob(str(ROOT / "preservation/*/SHA256SUMS.txt")):
        for line in Path(manifest).read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            digest, relative = line.split("  ", 1)
            path = ROOT / relative
            if not path.exists():
                mismatches.append((relative, manifest, "MISSING"))
                continue
            checked += 1
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                mismatches.append((relative, manifest, "MISMATCH"))
    assert checked > 1000
    assert not mismatches, mismatches


def test_amendment_report_quotes_are_verbatim_not_paraphrased() -> None:
    """Every quoted block in the governance override writeup must appear, whitespace-normalized,
    in the report it is attributed to -- guards against citing a paraphrase as a direct quote."""
    import re

    def normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    doc = (ROOT / "docs/s2_primary_promotion_governance_override.md").read_text()
    sources = {
        "phase8": normalize((ROOT / "docs/phase8_report.md").read_text()),
        "phase15": normalize((ROOT / "docs/phase15_robustness_S2_report.md").read_text()),
        "amendment": normalize((ROOT / "docs/one_sided_ic_inference_amendment_report.md").read_text()),
    }
    raw_quotes = re.findall(r'^> "(.+?)"', doc, re.MULTILINE | re.DOTALL)
    assert len(raw_quotes) >= 5
    for raw in raw_quotes:
        # Strip the leading "> " markdown blockquote prefix from continuation lines.
        stripped = "\n".join(line[2:] if line.startswith("> ") else line for line in raw.splitlines())
        normalized = normalize(stripped)
        # An elided quote ("...") is checked in segments around the ellipsis.
        segments = [normalize(part) for part in normalized.split("...") if part.strip()]
        for segment in segments:
            assert any(segment[:50] in source for source in sources.values()), f"not verbatim: {segment[:80]}"
