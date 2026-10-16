"""Compare Phase 7B candidate-history outputs with member-history baseline."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=Path("baseline/corrected_universe_member_history_phase7b/results_tables"))
    parser.add_argument("--tables-dir", type=Path, default=Path("results/tables"))
    args = parser.parse_args()
    baseline, output = args.baseline, args.tables_dir

    old_summary = pd.read_csv(baseline / "phase7_s0_s1_summary.csv")
    new_summary = pd.read_csv(output / "phase7b_phase7_s0_s1_summary.csv")
    metrics = ["mean_ic", "hac5_ic_t", "annualized_icir", "positive_ic_fraction", "ls_mean", "ls_sharpe", "ls_hac5_t", "ls_cumulative_gross", "decile_monotonic_spearman", "decile_nonnegative_steps", "days"]
    old = old_summary[["signal"] + metrics].rename(columns={metric: f"member_history_{metric}" for metric in metrics})
    new = new_summary[["signal"] + metrics + ["one_sided_hac_ic_p_greater_zero", "one_sided_hac_ls_p_greater_zero"]].rename(columns={metric: f"candidate_history_{metric}" for metric in metrics})
    comparison = old.merge(new, on="signal", validate="one_to_one")
    for metric in metrics:
        comparison[f"delta_{metric}"] = comparison[f"candidate_history_{metric}"] - comparison[f"member_history_{metric}"]
    comparison["member_history_one_sided_hac_ic_p_greater_zero"] = stats.norm.sf(comparison["member_history_hac5_ic_t"])
    comparison["member_history_one_sided_hac_ls_p_greater_zero"] = stats.norm.sf(comparison["member_history_ls_hac5_t"])
    comparison.to_csv(output / "phase7b_candidate_history_phase7_comparison.csv", index=False)

    old_pair = pd.read_csv(baseline / "phase7_paired_differences.csv")
    new_pair = pd.read_csv(output / "phase7b_phase7_paired_differences.csv")
    pair = pd.DataFrame({
        "metric": ["IC_difference_S1_minus_S0", "long_short_difference_S1_minus_S0"],
        "member_history_mean": [old_pair.iloc[0]["mean_ic_difference_s1_minus_s0"], old_pair.iloc[0]["mean_long_short_difference_s1_minus_s0"]],
        "member_history_hac5_t": [old_pair.iloc[0]["hac5_ic_difference_t"], old_pair.iloc[0]["hac5_long_short_difference_t"]],
        "candidate_history_mean": [new_pair.iloc[0]["mean_ic_difference_s1_minus_s0"], new_pair.iloc[0]["mean_long_short_difference_s1_minus_s0"]],
        "candidate_history_hac5_t": [new_pair.iloc[0]["hac5_ic_difference_t"], new_pair.iloc[0]["hac5_long_short_difference_t"]],
        "candidate_history_one_sided_hac_p_greater_zero": [new_pair.iloc[0]["one_sided_hac_ic_difference_p_greater_zero"], new_pair.iloc[0]["one_sided_hac_long_short_difference_p_greater_zero"]],
    })
    pair["member_history_one_sided_hac_p_greater_zero"] = stats.norm.sf(pair["member_history_hac5_t"])
    pair["delta_mean"] = pair["candidate_history_mean"] - pair["member_history_mean"]
    pair.to_csv(output / "phase7b_candidate_history_paired_comparison.csv", index=False)

    old_elig = pd.read_csv(baseline / "phase7_eligibility_summary.csv").set_index("s1_status")["rows"]
    new_elig = pd.read_csv(output / "phase7b_phase7_eligibility_summary.csv").set_index("s1_status")["rows"]
    eligibility = pd.concat([old_elig.rename("member_history_rows"), new_elig.rename("candidate_history_rows")], axis=1).fillna(0).reset_index()
    eligibility["delta_rows"] = eligibility["candidate_history_rows"] - eligibility["member_history_rows"]
    eligibility.to_csv(output / "phase7b_candidate_history_eligibility_comparison.csv", index=False)

    pairs = [("q", "same_day_oc_return"), ("q", "volume_surprise"), ("q", "realized_volatility"), ("S0", "forward_oc_return")]
    old_corr = pd.read_csv(baseline / "phase6_correlation_summary.csv")
    new_corr = pd.read_csv(output / "phase7b_phase6_correlation_summary.csv")
    old_corr = old_corr.loc[[tuple(row) in pairs for row in old_corr[["variable_1", "variable_2"]].to_numpy()]]
    new_corr = new_corr.loc[[tuple(row) in pairs for row in new_corr[["variable_1", "variable_2"]].to_numpy()]]
    confound = old_corr[["variable_1", "variable_2", "mean_daily_spearman", "hac5_t"]].merge(new_corr[["variable_1", "variable_2", "mean_daily_spearman", "hac5_t"]], on=["variable_1", "variable_2"], suffixes=("_member_history", "_candidate_history"), validate="one_to_one")
    confound["delta_mean_daily_spearman"] = confound["mean_daily_spearman_candidate_history"] - confound["mean_daily_spearman_member_history"]
    confound.to_csv(output / "phase7b_candidate_history_confound_comparison.csv", index=False)

    old_reg = pd.read_csv(baseline / "phase6_regression_summary.csv").query("coefficient == 'rank_S0'")
    new_reg = pd.read_csv(output / "phase7b_phase6_regression_summary.csv").query("coefficient == 'rank_S0'")
    reg = old_reg[["model", "mean_coefficient", "hac5_t", "mean_daily_observations"]].merge(new_reg[["model", "mean_coefficient", "hac5_t", "mean_daily_observations"]], on="model", suffixes=("_member_history", "_candidate_history"), validate="one_to_one")
    reg.to_csv(output / "phase7b_candidate_history_regression_comparison.csv", index=False)
    print(comparison.to_string(index=False))
    print(pair.to_string(index=False))
    print(eligibility.to_string(index=False))


if __name__ == "__main__":
    main()
