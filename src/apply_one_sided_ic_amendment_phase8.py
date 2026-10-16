"""Re-derive the Phase 8 leading-candidate decision under the amended
one-sided IC primary rule (see `one_sided_ic_inference.py`), 2026-09-12.

This reads only the already-persisted, unchanged Phase 8 result tables
(`phase8_common_sample_performance.csv`, `phase8_paired_differences.csv`,
`phase8_common_sample_coverage.csv`, `phase8_state_cell_size_summary.csv`) and
mirrors the decision block in `evaluate_conditional_signal_phase8.py` exactly.
It does not recompute any signal, panel, mean, standard error, or t-statistic;
it only re-derives the pass/fail label attached to the unchanged S2 HAC(5) IC
t-statistic in each sample.

IMPORTANT: this writes to a NEW file,
`phase8_decision_rule_evaluation_one_sided_amendment_2026-09-12.json`, and
never overwrites the original `phase8_decision_rule_evaluation.json`. That
original file's checksum is pinned as a frozen source artifact in the Phase 9,
10, and 11 preservation manifests (`preservation/phase{9,10,11}_*/SHA256SUMS.txt`);
overwriting it in place would break those phases' frozen-input guarantee. This
follows the same pattern this project already uses for the liquidity-window
correction and the Phase 7B candidate-history layer: a superseding result gets
a new, clearly labeled artifact, and the original is preserved unchanged.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from one_sided_ic_inference import ONE_SIDED_IC_CRITICAL_VALUE, ic_clears_one_sided_bar, ic_clears_two_sided_bar_superseded

SAMPLES = ["additional_2023-01-03_2025-05-27", "original_2025-05-28_2026-08-31"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tables-dir", type=Path, default=Path("results/tables"))
    args = parser.parse_args()

    summary = pd.read_csv(args.tables_dir / "phase8_common_sample_performance.csv")
    paired = pd.read_csv(args.tables_dir / "phase8_paired_differences.csv")
    coverage = pd.read_csv(args.tables_dir / "phase8_common_sample_coverage.csv")
    cell_summary = pd.read_csv(args.tables_dir / "phase8_state_cell_size_summary.csv")

    decision = {}
    for sample in SAMPLES:
        s1 = summary.query("sample == @sample and signal == 'S1'").iloc[0]
        s2 = summary.query("sample == @sample and signal == 'S2'").iloc[0]
        diff = paired.query("sample == @sample and comparison == 'S2_minus_S1'").iloc[0]
        decision[sample] = {
            "positive_s2_ic": bool(s2.mean_ic > 0),
            # Amended 2026-09-12: one-sided primary rule (H0: mean IC <= 0), t >= 1.645.
            # Supersedes the prior two-sided |t| >= 2 primary rule, retained below for audit only.
            "s2_hac5_ic_t_at_least_1_645_one_sided_primary": ic_clears_one_sided_bar(s2.hac5_ic_t),
            "one_sided_ic_critical_value": ONE_SIDED_IC_CRITICAL_VALUE,
            "s2_hac5_ic_t_at_least_2_two_sided_superseded": ic_clears_two_sided_bar_superseded(s2.hac5_ic_t),
            "s2_minus_s1_ic_positive": bool(diff.mean_ic_difference > 0),
            "s2_decile_monotonicity_not_worse": bool(s2.decile_monotonic_spearman >= s1.decile_monotonic_spearman),
            "coverage_not_materially_reduced": bool(coverage.query("sample == @sample").iloc[0].s2_common_retained_from_s1 >= .99),
            "small_cell_fraction": float(cell_summary.query("sample == @sample").iloc[0].small_cell_fraction),
        }
    output_path = args.tables_dir / "phase8_decision_rule_evaluation_one_sided_amendment_2026-09-12.json"
    output_path.write_text(json.dumps(decision, indent=2) + "\n")
    print(json.dumps(decision, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
