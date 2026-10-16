"""Phase 7B frozen Phase 6/7 evaluation using all-candidate feature histories."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from candidate_history_features import add_candidate_history_features


START, END, HAC = "2025-05-28", "2026-08-31", 5
SUBS = [("subperiod_1", "2025-05-28", "2026-01-13"), ("subperiod_2", "2026-01-14", "2026-08-31")]
VARIABLES = ["q", "S0", "same_day_oc_return", "reversal", "volume_surprise", "realized_volatility", "forward_oc_return"]


def hac_mean(series: pd.Series) -> tuple[float, float, float, float]:
    values = series.dropna().astype(float).to_numpy()
    fit = sm.OLS(values, np.ones((len(values), 1))).fit(cov_type="HAC", cov_kwds={"maxlags": HAC})
    estimate, se, t = float(fit.params[0]), float(fit.bse[0]), float(fit.tvalues[0])
    return estimate, se, t, float(stats.norm.sf(t))


def rank_scaled(series: pd.Series) -> pd.Series:
    count = series.notna().sum()
    return 2 * (series.rank(method="average") - 0.5) / count - 1


def quintiles(frame: pd.DataFrame, feature: str) -> pd.Series:
    output = pd.Series(pd.NA, index=frame.index, dtype="Int64")
    for _, group in frame.loc[frame[feature].notna()].sort_values(["Date", feature, "canonical_research_symbol"]).groupby("Date"):
        ranks = group[feature].rank(method="first")
        output.loc[group.index] = (np.floor((ranks - 1) * 5 / len(group)).astype(int) + 1).astype("Int64")
    return output


def signal_eval(frame: pd.DataFrame, signal: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, float]]:
    ranked = frame[["Date", "canonical_research_symbol", "forward_oc_return", signal]].dropna().sort_values(["Date", signal, "canonical_research_symbol"]).copy()
    ranked["rank"] = ranked.groupby("Date")[signal].rank(method="first")
    ranked["n"] = ranked.groupby("Date")[signal].transform("size")
    ranked["decile"] = np.floor((ranked["rank"] - 1) * 10 / ranked["n"]).astype(int) + 1
    ic = ranked.groupby("Date").apply(
        lambda group: stats.spearmanr(group[signal], group["forward_oc_return"]).statistic,
        include_groups=False,
    ).rename("rank_ic").reset_index()
    decile_daily = ranked.groupby(["Date", "decile"], observed=True)["forward_oc_return"].mean().reset_index()
    decile_rows = []
    for decile, group in decile_daily.groupby("decile", observed=True):
        mean, se, t, p = hac_mean(group["forward_oc_return"])
        decile_rows.append({"decile": int(decile), "mean_return": mean, "hac5_se": se, "hac5_t": t, "one_sided_hac_p_greater_zero": p, "days": len(group)})
    deciles = pd.DataFrame(decile_rows).sort_values("decile")
    long_short = decile_daily.pivot(index="Date", columns="decile", values="forward_oc_return")
    long_short["long_short"] = long_short[10] - long_short[1]
    long_short = long_short.reset_index()
    mean_ic, se_ic, t_ic, p_ic = hac_mean(ic["rank_ic"])
    mean_ls, se_ls, t_ls, p_ls = hac_mean(long_short["long_short"])
    ic_std, ls_std = float(ic["rank_ic"].std(ddof=1)), float(long_short["long_short"].std(ddof=1))
    summary = {
        "mean_ic": mean_ic, "hac5_ic_se": se_ic, "hac5_ic_t": t_ic, "one_sided_hac_ic_p_greater_zero": p_ic,
        "ic_std": ic_std, "annualized_icir": mean_ic / ic_std * np.sqrt(252), "positive_ic_fraction": float((ic["rank_ic"] > 0).mean()),
        "ls_mean": mean_ls, "ls_hac5_se": se_ls, "ls_hac5_t": t_ls, "one_sided_hac_ls_p_greater_zero": p_ls,
        "ls_annualized_arithmetic": mean_ls * 252, "ls_annualized_volatility": ls_std * np.sqrt(252),
        "ls_sharpe": mean_ls / ls_std * np.sqrt(252), "ls_cumulative_gross": float((1 + long_short["long_short"]).prod() - 1),
        "decile_monotonic_spearman": float(stats.spearmanr(deciles["decile"], deciles["mean_return"]).statistic),
        "decile_nonnegative_steps": int((deciles["mean_return"].diff().dropna() >= 0).sum()), "days": len(ic),
    }
    return ranked, ic, deciles, long_short, summary


def phase6(evaluation: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    corr_rows = []
    for date, day in evaluation.groupby("Date"):
        for left, right in itertools.combinations(VARIABLES, 2):
            pair = day[[left, right]].dropna()
            value = stats.spearmanr(pair[left], pair[right]).statistic if len(pair) >= 10 and pair[left].nunique() > 1 and pair[right].nunique() > 1 else np.nan
            corr_rows.append({"Date": date, "variable_1": left, "variable_2": right, "spearman": value, "observations": len(pair)})
    corr_daily = pd.DataFrame(corr_rows)
    summary_rows = []
    for (left, right), group in corr_daily.groupby(["variable_1", "variable_2"]):
        mean, se, t, p = hac_mean(group["spearman"])
        summary_rows.append({"variable_1": left, "variable_2": right, "mean_daily_spearman": mean, "hac5_se": se, "hac5_t": t, "one_sided_hac_p_greater_zero": p, "positive_day_fraction": (group["spearman"] > 0).mean(), "same_sign_day_fraction": ((group["spearman"] > 0) if mean >= 0 else (group["spearman"] < 0)).mean(), "days": group["spearman"].notna().sum()})
    corr_summary = pd.DataFrame(summary_rows)
    sub_rows = []
    for name, start, end in SUBS:
        for (left, right), group in corr_daily.loc[corr_daily.Date.between(start, end)].groupby(["variable_1", "variable_2"]):
            mean, _, t, p = hac_mean(group["spearman"])
            sub_rows.append({"subperiod": name, "start": start, "end": end, "variable_1": left, "variable_2": right, "mean_daily_spearman": mean, "hac5_t": t, "one_sided_hac_p_greater_zero": p, "days": group["spearman"].notna().sum()})
    corr_sub = pd.DataFrame(sub_rows)

    quintile_rows = []
    work = evaluation.copy()
    for feature, bucket in [("same_day_oc_return", "same_day_return_quintile"), ("volume_surprise", "volume_surprise_quintile"), ("realized_volatility", "realized_volatility_quintile")]:
        work[bucket] = quintiles(work, feature)
        metrics = ["q", "S0", "forward_oc_return"] if feature == "same_day_oc_return" else ["q"]
        daily = work.groupby(["Date", bucket], observed=True)[metrics].mean().reset_index()
        for metric in metrics:
            for value, group in daily.groupby(bucket, observed=True):
                mean, se, t, p = hac_mean(group[metric])
                quintile_rows.append({"sort_feature": feature, "quintile": int(value), "metric": metric, "mean": mean, "hac5_se": se, "hac5_t": t, "one_sided_hac_p_greater_zero": p, "days": len(group)})
        if feature == "same_day_oc_return":
            ic_rows = []
            for (date, value), group in work.groupby(["Date", bucket], observed=True):
                pair = group[["S0", "forward_oc_return"]].dropna()
                ic_rows.append({"Date": date, "quintile": int(value), "within_quintile_s0_ic": stats.spearmanr(pair["S0"], pair["forward_oc_return"]).statistic if len(pair) >= 10 and pair["S0"].nunique() > 1 else np.nan})
            for value, group in pd.DataFrame(ic_rows).groupby("quintile"):
                mean, se, t, p = hac_mean(group["within_quintile_s0_ic"])
                quintile_rows.append({"sort_feature": feature, "quintile": int(value), "metric": "within_quintile_s0_ic", "mean": mean, "hac5_se": se, "hac5_t": t, "one_sided_hac_p_greater_zero": p, "days": len(group)})
    quintile_summary = pd.DataFrame(quintile_rows)

    common_vars = ["forward_oc_return", "S0", "reversal", "volume_surprise", "realized_volatility"]
    common = evaluation.dropna(subset=common_vars).copy()
    for variable in common_vars[1:]:
        common[f"rank_{variable}"] = common.groupby("Date")[variable].transform(rank_scaled)
    specs = {"model_1_s0": ["rank_S0"], "model_2_s0_reversal": ["rank_S0", "rank_reversal"], "model_3_all_controls": ["rank_S0", "rank_reversal", "rank_volume_surprise", "rank_realized_volatility"]}
    coefficient_rows = []
    for date, day in common.groupby("Date"):
        for model, predictors in specs.items():
            fit = sm.OLS(day["forward_oc_return"].astype(float), sm.add_constant(day[predictors].astype(float), has_constant="add")).fit()
            for coefficient, value in fit.params.items():
                coefficient_rows.append({"Date": date, "model": model, "coefficient": coefficient, "value": value, "observations": len(day)})
    coefficients = pd.DataFrame(coefficient_rows)
    coefficient_summary_rows = []
    for (model, coefficient), group in coefficients.groupby(["model", "coefficient"]):
        mean, se, t, p = hac_mean(group["value"])
        coefficient_summary_rows.append({"model": model, "coefficient": coefficient, "mean_coefficient": mean, "hac5_se": se, "hac5_t": t, "one_sided_hac_p_greater_zero": p, "days": len(group), "mean_daily_observations": group["observations"].mean()})
    return corr_daily, corr_summary, corr_sub, quintile_summary, coefficients, pd.DataFrame(coefficient_summary_rows), common


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--tables-dir", type=Path, default=Path("results/tables"))
    parser.add_argument("--figures-dir", type=Path, default=Path("results/figures"))
    args = parser.parse_args(); args.tables_dir.mkdir(parents=True, exist_ok=True); args.figures_dir.mkdir(parents=True, exist_ok=True)
    raw = pd.read_parquet(args.processed_dir / "candidate_history_panel.parquet")
    featured = add_candidate_history_features(raw)
    target = pd.read_parquet(args.processed_dir / "master_stock_day_with_target.parquet")
    target = target[["Date", "canonical_research_symbol", "designated_target_date", "next_session_adjusted_open", "next_session_adjusted_close", "forward_oc_return", "target_status", "target_available"]]
    if target.duplicated(["Date", "canonical_research_symbol"]).any():
        raise ValueError("Target lookup has duplicate keys")
    featured = featured.merge(target, on=["Date", "canonical_research_symbol"], how="left", validate="one_to_one")
    featured.to_parquet(args.processed_dir / "candidate_history_feature_panel.parquet", index=False)

    evaluation = featured.loc[featured["Date"].between(START, END) & featured["universe_member"]].copy()
    if not evaluation.groupby("Date").size().eq(400).all() or evaluation["Date"].nunique() != 317:
        raise ValueError("Signal-date evaluation membership is not the corrected top-400 universe")
    full_s0 = evaluation.loc[evaluation["q"].notna() & evaluation["target_available"] & evaluation["forward_oc_return"].notna()].copy()
    _, full_s0_ic, full_s0_dec, full_s0_ls, full_s0_summary = signal_eval(full_s0, "S0")
    baseline_ic = pd.read_csv(args.tables_dir / "phase5_daily_rank_ic.csv", parse_dates=["Date"])
    check = full_s0_ic.merge(baseline_ic, on="Date", suffixes=("_candidate_history", "_baseline"), validate="one_to_one")
    if len(check) != len(baseline_ic) or not np.allclose(check["rank_ic_candidate_history"], check["rank_ic_baseline"], rtol=0, atol=1e-15):
        raise AssertionError("Full-sample S0 changed under candidate-history architecture")
    pd.DataFrame([{**{"signal": "S0_full_sample"}, **full_s0_summary, "matches_phase5_daily_ic_exactly": True}]).to_csv(args.tables_dir / "phase7b_s0_full_sample_validation.csv", index=False)

    corr_daily, corr_summary, corr_sub, quintile_summary, coefficients, coefficient_summary, common = phase6(evaluation)
    corr_daily.to_csv(args.tables_dir / "phase7b_phase6_daily_correlations.csv", index=False)
    corr_summary.to_csv(args.tables_dir / "phase7b_phase6_correlation_summary.csv", index=False)
    corr_sub.to_csv(args.tables_dir / "phase7b_phase6_correlation_subperiods.csv", index=False)
    quintile_summary.to_csv(args.tables_dir / "phase7b_phase6_quintile_summary.csv", index=False)
    coefficients.to_csv(args.tables_dir / "phase7b_phase6_daily_regression_coefficients.csv", index=False)
    coefficient_summary.to_csv(args.tables_dir / "phase7b_phase6_regression_summary.csv", index=False)
    evaluation.to_parquet(args.processed_dir / "phase7b_phase6_evaluation_panel.parquet", index=False)

    evaluation["s1_eligible"] = evaluation["S1"].notna() & evaluation["target_available"] & evaluation["forward_oc_return"].notna()
    evaluation["s1_status"] = "eligible"
    evaluation.loc[evaluation["q"].isna(), "s1_status"] = "current_q_missing"
    evaluation.loc[evaluation["q"].notna() & ~evaluation["exact_60_valid_history"], "s1_status"] = "missing_finra_history"
    evaluation.loc[evaluation["S1"].notna() & ~evaluation["target_available"], "s1_status"] = "missing_target"
    evaluation.loc[evaluation["s1_eligible"], "s1_status"] = "eligible"
    paired = evaluation.loc[evaluation["s1_eligible"]].copy()
    _, s0_ic, s0_dec, s0_ls, s0_summary = signal_eval(paired, "S0")
    _, s1_ic, s1_dec, s1_ls, s1_summary = signal_eval(paired, "S1")
    ic_pair = s1_ic.merge(s0_ic, on="Date", suffixes=("_s1", "_s0"), validate="one_to_one")
    ic_pair["ic_difference"] = ic_pair["rank_ic_s1"] - ic_pair["rank_ic_s0"]
    ls_pair = s1_ls.merge(s0_ls, on="Date", suffixes=("_s1", "_s0"), validate="one_to_one")
    ls_pair["long_short_difference"] = ls_pair["long_short_s1"] - ls_pair["long_short_s0"]
    ic_diff, ic_diff_se, ic_diff_t, ic_diff_p = hac_mean(ic_pair["ic_difference"])
    ls_diff, ls_diff_se, ls_diff_t, ls_diff_p = hac_mean(ls_pair["long_short_difference"])
    rank_corr = paired.groupby("Date").apply(lambda group: stats.spearmanr(group["S0"], group["S1"]).statistic, include_groups=False).rename("s0_s1_rank_correlation").reset_index()
    rank_corr_mean, rank_corr_se, rank_corr_t, rank_corr_p = hac_mean(rank_corr["s0_s1_rank_correlation"])
    summary = pd.DataFrame([{**{"signal": "S0_paired"}, **s0_summary}, {**{"signal": "S1"}, **s1_summary}])
    paired_summary = pd.DataFrame([{
        "mean_ic_difference_s1_minus_s0": ic_diff, "hac5_ic_difference_se": ic_diff_se, "hac5_ic_difference_t": ic_diff_t, "one_sided_hac_ic_difference_p_greater_zero": ic_diff_p,
        "mean_long_short_difference_s1_minus_s0": ls_diff, "hac5_long_short_difference_se": ls_diff_se, "hac5_long_short_difference_t": ls_diff_t, "one_sided_hac_long_short_difference_p_greater_zero": ls_diff_p,
        "mean_daily_s0_s1_rank_correlation": rank_corr_mean, "hac5_rank_correlation_t": rank_corr_t, "one_sided_hac_rank_correlation_p_greater_zero": rank_corr_p,
    }])
    sub_rows = []
    for name, start, end in SUBS:
        for signal, table in [("S0", s0_ic), ("S1", s1_ic)]:
            values = table.loc[table["Date"].between(start, end), "rank_ic"]
            mean, _, t, p = hac_mean(values)
            sub_rows.append({"signal": signal, "subperiod": name, "start": start, "end": end, "days": len(values), "mean_ic": mean, "hac5_t": t, "one_sided_hac_p_greater_zero": p})
    eligibility = evaluation.groupby("s1_status", as_index=False).size().rename(columns={"size": "rows"})
    daily_eligibility = evaluation.groupby("Date").agg(rows=("Date", "size"), eligible=("s1_eligible", "sum"), current_q_missing=("q", lambda series: series.isna().sum()), missing_finra_history=("exact_60_valid_history", lambda series: (~series).sum()), near_zero_mad=("near_zero_mad", "sum")).reset_index()
    security_eligibility = evaluation.groupby("canonical_research_symbol").agg(rows=("Date", "size"), eligible=("s1_eligible", "sum"), missing_finra_history=("exact_60_valid_history", lambda series: (~series).sum())).reset_index()
    distributions = []
    for column in ["historical_median", "historical_mad", "z", "S1"]:
        values = evaluation[column].dropna()
        distributions.append({"variable": column, "n": len(values), "mean": values.mean(), "std": values.std(ddof=1), "min": values.min(), "p01": values.quantile(.01), "p50": values.median(), "p99": values.quantile(.99), "max": values.max()})
    extreme = evaluation.loc[evaluation["z"].notna(), ["Date", "canonical_research_symbol", "q", "historical_median", "historical_mad", "z", "S1", "near_zero_mad", "forward_oc_return"]].assign(abs_z=lambda frame: frame["z"].abs()).sort_values(["abs_z", "Date", "canonical_research_symbol"], ascending=[False, True, True]).head(100)

    summary.to_csv(args.tables_dir / "phase7b_phase7_s0_s1_summary.csv", index=False)
    paired_summary.to_csv(args.tables_dir / "phase7b_phase7_paired_differences.csv", index=False)
    s0_ic.to_csv(args.tables_dir / "phase7b_phase7_daily_ic_s0_paired.csv", index=False); s1_ic.to_csv(args.tables_dir / "phase7b_phase7_daily_ic_s1.csv", index=False)
    s0_ls.to_csv(args.tables_dir / "phase7b_phase7_daily_ls_s0_paired.csv", index=False); s1_ls.to_csv(args.tables_dir / "phase7b_phase7_daily_ls_s1.csv", index=False)
    s0_dec.to_csv(args.tables_dir / "phase7b_phase7_deciles_s0_paired.csv", index=False); s1_dec.to_csv(args.tables_dir / "phase7b_phase7_deciles_s1.csv", index=False)
    pd.DataFrame(sub_rows).to_csv(args.tables_dir / "phase7b_phase7_subperiod_ic.csv", index=False)
    rank_corr.to_csv(args.tables_dir / "phase7b_phase7_daily_s0_s1_rank_correlation.csv", index=False)
    eligibility.to_csv(args.tables_dir / "phase7b_phase7_eligibility_summary.csv", index=False)
    daily_eligibility.to_csv(args.tables_dir / "phase7b_phase7_daily_eligibility.csv", index=False)
    security_eligibility.to_csv(args.tables_dir / "phase7b_phase7_security_eligibility.csv", index=False)
    pd.DataFrame(distributions).to_csv(args.tables_dir / "phase7b_phase7_distributions.csv", index=False)
    extreme.to_csv(args.tables_dir / "phase7b_phase7_extreme_z.csv", index=False)
    evaluation.to_parquet(args.processed_dir / "phase7b_phase7_evaluation_panel.parquet", index=False)

    for deciles, label, color in [(s0_dec, "S0", "#888888"), (s1_dec, "S1", "#2455a6")]:
        plt.errorbar(deciles["decile"], deciles["mean_return"], yerr=1.96 * deciles["hac5_se"], fmt="o-", label=label, color=color, capsize=3)
    plt.xlabel("Decile (10 = highest alpha)"); plt.ylabel("Mean next-session O-C return"); plt.legend(); plt.tight_layout(); plt.savefig(args.figures_dir / "phase7b_s0_s1_decile_comparison.png", dpi=150); plt.close()
    for series, label, color in [(s0_ls, "S0", "#888888"), (s1_ls, "S1", "#2455a6")]:
        plt.plot(series["Date"], (1 + series["long_short"]).cumprod() - 1, label=label, color=color)
    plt.ylabel("Cumulative gross D10-D1 return"); plt.legend(); plt.tight_layout(); plt.savefig(args.figures_dir / "phase7b_s0_s1_cumulative_comparison.png", dpi=150); plt.close()
    s0_ic["rolling_60d_ic"] = s0_ic["rank_ic"].rolling(60).mean(); s1_ic["rolling_60d_ic"] = s1_ic["rank_ic"].rolling(60).mean()
    plt.plot(s0_ic["Date"], s0_ic["rolling_60d_ic"], label="S0", color="#888888"); plt.plot(s1_ic["Date"], s1_ic["rolling_60d_ic"], label="S1", color="#2455a6"); plt.axhline(0, color="black", lw=.6); plt.legend(); plt.ylabel("60-day mean Rank IC"); plt.tight_layout(); plt.savefig(args.figures_dir / "phase7b_s0_s1_rolling_ic.png", dpi=150); plt.close()
    for feature, filename, label in [("same_day_oc_return", "phase7b_phase6_q_by_same_day_return_quintile.png", "Same-day return quintile"), ("volume_surprise", "phase7b_phase6_q_by_volume_surprise_quintile.png", "Volume-surprise quintile"), ("realized_volatility", "phase7b_phase6_q_by_realized_volatility_quintile.png", "Prior realized-volatility quintile")]:
        chart = quintile_summary.query("sort_feature == @feature and metric == 'q'").sort_values("quintile")
        plt.figure(figsize=(6, 4)); plt.errorbar(chart["quintile"], chart["mean"], yerr=1.96 * chart["hac5_se"], fmt="o-", capsize=3); plt.xlabel(label); plt.ylabel("Mean q"); plt.tight_layout(); plt.savefig(args.figures_dir / filename, dpi=150); plt.close()
    s0_coef = coefficient_summary.query("coefficient == 'rank_S0'").sort_values("model")
    plt.figure(figsize=(7, 4)); plt.errorbar(range(len(s0_coef)), s0_coef["mean_coefficient"], yerr=1.96 * s0_coef["hac5_se"], fmt="o", capsize=3); plt.xticks(range(len(s0_coef)), ["S0", "+ reversal", "+ reversal, volume, vol"]); plt.axhline(0, color="black", lw=.7); plt.ylabel("Mean daily S0 coefficient"); plt.tight_layout(); plt.savefig(args.figures_dir / "phase7b_phase6_s0_coefficient_by_model.png", dpi=150); plt.close()
    selected_pairs = [("q", "same_day_oc_return"), ("q", "volume_surprise"), ("q", "realized_volatility")]
    stable = corr_sub.set_index(["variable_1", "variable_2"]).loc[selected_pairs].reset_index().pivot(index=["variable_1", "variable_2"], columns="subperiod", values="mean_daily_spearman")
    stable.plot(kind="bar", figsize=(8, 4)); plt.ylabel("Mean daily Spearman"); plt.xticks(rotation=20, ha="right"); plt.tight_layout(); plt.savefig(args.figures_dir / "phase7b_phase6_confound_correlations_by_subperiod.png", dpi=150); plt.close()
    print(json.dumps({"candidate_rows": len(featured), "evaluation_rows": len(evaluation), "full_s0_rows": len(full_s0), "paired_s1_rows": len(paired), "phase6_common_rows": len(common)}, indent=2))


if __name__ == "__main__":
    main()
