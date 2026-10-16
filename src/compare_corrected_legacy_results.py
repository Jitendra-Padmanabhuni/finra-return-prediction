"""Create corrected-versus-legacy Phase 2–7 comparison tables."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def paired_rows(legacy: pd.DataFrame, corrected: pd.DataFrame, keys: list[str], metrics: list[str]) -> pd.DataFrame:
    left = legacy[keys + metrics].copy().rename(columns={m: f"legacy_{m}" for m in metrics})
    right = corrected[keys + metrics].copy().rename(columns={m: f"corrected_{m}" for m in metrics})
    output = left.merge(right, on=keys, how="outer", validate="one_to_one")
    for metric in metrics:
        output[f"delta_{metric}"] = output[f"corrected_{metric}"] - output[f"legacy_{metric}"]
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-root", type=Path, default=Path("legacy/expanding_liquidity_window/results_tables"))
    parser.add_argument("--corrected-root", type=Path, default=Path("results/tables"))
    args = parser.parse_args()
    legacy, corrected = args.legacy_root, args.corrected_root

    s0_metrics = [
        "mean_rank_ic", "hac5_ic_t", "annualized_icir", "positive_ic_day_fraction",
        "ls_mean_daily", "ls_sharpe", "ls_hac5_t", "ls_cumulative_gross_return", "eligible_rows",
    ]
    s0 = paired_rows(
        pd.read_csv(legacy / "phase5_naive_summary.csv").assign(signal="S0_full_sample"),
        pd.read_csv(corrected / "phase5_naive_summary.csv").assign(signal="S0_full_sample"),
        ["signal"], s0_metrics,
    )
    s0.to_csv(corrected / "liquidity_correction_s0_comparison.csv", index=False)

    p7_metrics = [
        "mean_ic", "hac5_ic_t", "annualized_icir", "positive_ic_fraction", "ls_mean",
        "ls_sharpe", "ls_hac5_t", "ls_cumulative_gross", "decile_monotonic_spearman",
        "decile_nonnegative_steps", "days",
    ]
    p7 = paired_rows(
        pd.read_csv(legacy / "phase7_s0_s1_summary.csv"),
        pd.read_csv(corrected / "phase7_s0_s1_summary.csv"),
        ["signal"], p7_metrics,
    )
    p7.to_csv(corrected / "liquidity_correction_s1_comparison.csv", index=False)

    diff_metrics = [
        "mean_ic_difference_s1_minus_s0", "hac5_ic_difference_t",
        "mean_long_short_difference_s1_minus_s0", "hac5_long_short_difference_t",
        "mean_daily_s0_s1_rank_correlation",
    ]
    diffs = paired_rows(
        pd.read_csv(legacy / "phase7_paired_differences.csv").assign(comparison="S1_minus_S0"),
        pd.read_csv(corrected / "phase7_paired_differences.csv").assign(comparison="S1_minus_S0"),
        ["comparison"], diff_metrics,
    )
    diffs.to_csv(corrected / "liquidity_correction_paired_comparison.csv", index=False)

    correlation_metrics = ["mean_daily_spearman", "hac5_t", "same_sign_day_fraction", "days"]
    confound_pairs = {
        ("q", "same_day_oc_return"), ("q", "volume_surprise"),
        ("q", "realized_volatility"), ("q", "forward_oc_return"),
        ("S0", "forward_oc_return"),
    }
    legacy_corr = pd.read_csv(legacy / "phase6_correlation_summary.csv")
    corrected_corr = pd.read_csv(corrected / "phase6_correlation_summary.csv")
    legacy_corr = legacy_corr.loc[[tuple(x) in confound_pairs for x in legacy_corr[["variable_1", "variable_2"]].to_numpy()]]
    corrected_corr = corrected_corr.loc[[tuple(x) in confound_pairs for x in corrected_corr[["variable_1", "variable_2"]].to_numpy()]]
    corr = paired_rows(legacy_corr, corrected_corr, ["variable_1", "variable_2"], correlation_metrics)
    corr.to_csv(corrected / "liquidity_correction_confound_correlation_comparison.csv", index=False)

    regression_metrics = ["mean_coefficient", "hac5_t", "mean_daily_observations"]
    legacy_reg = pd.read_csv(legacy / "phase6_regression_summary.csv").query("coefficient == 'rank_S0'")
    corrected_reg = pd.read_csv(corrected / "phase6_regression_summary.csv").query("coefficient == 'rank_S0'")
    reg = paired_rows(legacy_reg, corrected_reg, ["model", "coefficient"], regression_metrics)
    reg.to_csv(corrected / "liquidity_correction_confound_regression_comparison.csv", index=False)

    coverage_rows = []
    for label, root in [("legacy", legacy), ("corrected", corrected)]:
        p3 = pd.read_csv(root / "phase3_coverage_overall.csv")
        p4 = pd.read_csv(root / "phase4_target_coverage_overall.csv")
        p7e = pd.read_csv(root / "phase7_eligibility_summary.csv")
        for _, row in p3.iterrows():
            coverage_rows.append({"version": label, "phase": "3", "status": row["join_status"], "rows": row["rows"]})
        for _, row in p4.iterrows():
            coverage_rows.append({"version": label, "phase": "4", "status": row["target_status"], "rows": row["rows"]})
        for _, row in p7e.iterrows():
            coverage_rows.append({"version": label, "phase": "7", "status": row["s1_status"], "rows": row["rows"]})
    pd.DataFrame(coverage_rows).to_csv(corrected / "liquidity_correction_coverage_eligibility_comparison.csv", index=False)
    print(s0.to_string(index=False))
    print(p7.to_string(index=False))
    print(corr.to_string(index=False))
    print(reg.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
