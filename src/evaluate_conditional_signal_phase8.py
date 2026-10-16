"""Phase 8 frozen five-by-five conditional abnormal-short-volume signal."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from evaluate_candidate_history_phase7b import hac_mean, signal_eval


SAMPLES = {
    "additional_2023-01-03_2025-05-27": ("2023-01-03", "2025-05-27"),
    "original_2025-05-28_2026-08-31": ("2025-05-28", "2026-08-31"),
}
ORIGINAL_SUBPERIODS = [
    ("subperiod_1", "2025-05-28", "2026-01-13"),
    ("subperiod_2", "2026-01-14", "2026-08-31"),
]
HAC = 5


def stable_buckets(frame: pd.DataFrame, value: str, output: str) -> pd.DataFrame:
    """Assign five approximately equal independent daily buckets, alphabetically breaking ties."""
    result = frame.copy()
    result[output] = pd.Series(pd.NA, index=result.index, dtype="Int64")
    for _, day in result.groupby("Date", sort=False):
        ordered = day.sort_values([value, "canonical_research_symbol"], kind="stable")
        n = len(ordered)
        result.loc[ordered.index, output] = (np.floor(np.arange(n) * 5 / n).astype(int) + 1)
    return result


def form_s2(panel: pd.DataFrame, sample: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    start, end = SAMPLES[sample]
    eligible = panel.loc[
        panel["Date"].between(start, end)
        & panel["universe_member"]
        & panel["z"].notna()
        & panel["volume_surprise"].notna()
        & panel["realized_volatility"].notna()
    ].copy()
    if eligible.empty:
        raise ValueError(f"No S2 formation rows for {sample}")
    # This table intentionally excludes target fields until after formation.
    target_columns = {"forward_oc_return", "target_available", "designated_target_date", "next_session_adjusted_open", "next_session_adjusted_close"}
    if target_columns.intersection(eligible.columns):
        formation = eligible.drop(columns=list(target_columns.intersection(eligible.columns))).copy()
    else:
        formation = eligible.copy()
    formation = stable_buckets(formation, "volume_surprise", "vs_bucket")
    formation = stable_buckets(formation, "realized_volatility", "vol_bucket")
    formation["state_cell"] = (formation["vs_bucket"].astype(int) - 1) * 5 + formation["vol_bucket"].astype(int)
    formation["cell_size"] = formation.groupby(["Date", "state_cell"])["z"].transform("size")
    formation["cell_median_z"] = formation.groupby(["Date", "state_cell"])["z"].transform("median")
    formation["a"] = formation["z"] - formation["cell_median_z"]
    formation["S2"] = -formation["a"]
    formation["sample"] = sample
    if formation[["vs_bucket", "vol_bucket", "state_cell"]].isna().any().any():
        raise AssertionError("Eligible stock missing a conditioning assignment")
    if formation.duplicated(["Date", "canonical_research_symbol"]).any():
        raise AssertionError("S2 formation produced duplicate stock-date rows")
    zero_medians = formation.groupby(["Date", "state_cell"])["a"].median().abs()
    if not np.allclose(zero_medians, 0, atol=1e-12, rtol=0):
        raise AssertionError("Within-cell median residual is not zero")
    cell_sizes = formation.groupby(["Date", "state_cell"], as_index=False).agg(
        cell_size=("cell_size", "first"),
        cell_median_z=("cell_median_z", "first"),
        small_cell_lt10=("cell_size", lambda values: bool(values.iloc[0] < 10)),
    )
    cell_sizes["sample"] = sample
    return formation, cell_sizes


def max_drawdown(series: pd.Series) -> float:
    wealth = (1 + series.fillna(0)).cumprod()
    return float((wealth / wealth.cummax() - 1).min())


def evaluate_common(common: pd.DataFrame, sample: str):
    results: dict[str, tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, float]]] = {}
    for signal in ["S0", "S1", "S2"]:
        ranked, ic, deciles, ls, summary = signal_eval(common, signal)
        summary.update({
            "sample": sample,
            "signal": signal,
            "common_stock_days": len(common),
            "ls_max_drawdown": max_drawdown(ls["long_short"]),
        })
        results[signal] = (ranked, ic.assign(sample=sample, signal=signal), deciles.assign(sample=sample, signal=signal), ls.assign(sample=sample, signal=signal), summary)
    paired_rows = []
    paired_daily = []
    for base in ["S1", "S0"]:
        ic = results["S2"][1][["Date", "rank_ic"]].merge(results[base][1][["Date", "rank_ic"]], on="Date", suffixes=("_s2", "_base"), validate="one_to_one")
        ic["difference"] = ic["rank_ic_s2"] - ic["rank_ic_base"]
        ls = results["S2"][3][["Date", "long_short"]].merge(results[base][3][["Date", "long_short"]], on="Date", suffixes=("_s2", "_base"), validate="one_to_one")
        ls["difference"] = ls["long_short_s2"] - ls["long_short_base"]
        ic_mean, ic_se, ic_t, ic_p = hac_mean(ic["difference"])
        ls_mean, ls_se, ls_t, ls_p = hac_mean(ls["difference"])
        paired_rows.append({"sample": sample, "comparison": f"S2_minus_{base}", "mean_ic_difference": ic_mean, "hac5_ic_se": ic_se, "hac5_ic_t": ic_t, "one_sided_hac_ic_p_greater_zero": ic_p, "mean_long_short_difference": ls_mean, "hac5_long_short_se": ls_se, "hac5_long_short_t": ls_t, "one_sided_hac_long_short_p_greater_zero": ls_p})
        paired_daily.extend([
            ic.assign(sample=sample, comparison=f"S2_minus_{base}", metric="rank_ic_difference"),
            ls.assign(sample=sample, comparison=f"S2_minus_{base}", metric="long_short_difference"),
        ])
    corr_rows = []
    for date, day in common.groupby("Date"):
        for left, right in [("S0", "S1"), ("S0", "S2"), ("S1", "S2")]:
            corr_rows.append({"sample": sample, "Date": date, "left": left, "right": right, "rank_correlation": stats.spearmanr(day[left], day[right]).statistic, "observations": len(day)})
    return results, pd.DataFrame(paired_rows), pd.concat(paired_daily, ignore_index=True), pd.DataFrame(corr_rows)


def dependence_summary(common: pd.DataFrame, sample: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    daily = []
    for date, day in common.groupby("Date"):
        for signal in ["S1", "S2"]:
            for variable in ["volume_surprise", "realized_volatility", "same_day_oc_return", "reversal"]:
                pair = day[[signal, variable]].dropna()
                value = stats.spearmanr(pair[signal], pair[variable]).statistic if len(pair) >= 10 else np.nan
                daily.append({"sample": sample, "Date": date, "signal": signal, "variable": variable, "spearman": value, "observations": len(pair)})
    daily_frame = pd.DataFrame(daily)
    for (signal, variable), values in daily_frame.groupby(["signal", "variable"]):
        mean, se, t, p = hac_mean(values["spearman"])
        rows.append({"sample": sample, "signal": signal, "variable": variable, "mean_daily_spearman": mean, "hac5_se": se, "hac5_t": t, "one_sided_hac_p_greater_zero": p, "same_sign_day_fraction": ((values["spearman"] > 0) if mean >= 0 else (values["spearman"] < 0)).mean(), "days": values["spearman"].notna().sum()})
    return pd.DataFrame(rows), daily_frame


def grouped_results(ic: pd.DataFrame, ls: pd.DataFrame, grouping: str) -> pd.DataFrame:
    i = ic.copy(); l = ls.copy()
    i["group"] = i.Date.dt.year.astype(str) if grouping == "year" else i.Date.dt.to_period("M").astype(str)
    l["group"] = l.Date.dt.year.astype(str) if grouping == "year" else l.Date.dt.to_period("M").astype(str)
    rows = []
    for (sample, signal, group), values in i.groupby(["sample", "signal", "group"]):
        long_short = l.loc[(l["sample"] == sample) & (l["signal"] == signal) & (l["group"] == group), "long_short"]
        mean, se, t, p = hac_mean(values["rank_ic"])
        ls_mean, ls_se, ls_t, ls_p = hac_mean(long_short)
        ls_std = long_short.std(ddof=1)
        rows.append({"sample": sample, "signal": signal, grouping: group, "days": len(values), "mean_ic": mean, "hac5_ic_se": se, "hac5_ic_t": t, "one_sided_hac_ic_p_greater_zero": p, "positive_ic_fraction": (values.rank_ic > 0).mean(), "ls_mean": ls_mean, "hac5_ls_se": ls_se, "hac5_ls_t": ls_t, "one_sided_hac_ls_p_greater_zero": ls_p, "ls_sharpe": ls_mean / ls_std * np.sqrt(252) if ls_std > 0 else np.nan, "ls_cumulative_gross": (1 + long_short).prod() - 1, "ls_max_drawdown": max_drawdown(long_short)})
    return pd.DataFrame(rows)


def globe_life_diagnostic(results: dict, common: pd.DataFrame, sample: str) -> pd.DataFrame:
    target_date = pd.Timestamp("2024-04-10")
    rows = []
    for signal, result in results.items():
        ranked, _, _, ls, _ = result
        matches = ranked.loc[(ranked.Date == target_date) & ranked.canonical_research_symbol.str.endswith("_symbol_GL")].copy()
        for row in matches.itertuples(index=False):
            daily = ls.loc[ls.Date.eq(target_date)].iloc[0]
            rows.append({"sample": sample, "signal": signal, "signal_date": target_date, "canonical_research_symbol": row.canonical_research_symbol, "decile": row.decile, "decile_size": int((ranked.Date.eq(target_date) & ranked.decile.eq(row.decile)).sum()), "forward_oc_return": row.forward_oc_return, "gross_contribution_to_its_decile_mean": row.forward_oc_return / int((ranked.Date.eq(target_date) & ranked.decile.eq(row.decile)).sum()), "daily_d10_minus_d1": daily.long_short, "in_extreme_decile": row.decile in {1, 10}})
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--tables-dir", type=Path, default=Path("results/tables"))
    parser.add_argument("--figures-dir", type=Path, default=Path("results/figures"))
    args = parser.parse_args(); args.tables_dir.mkdir(parents=True, exist_ok=True); args.figures_dir.mkdir(parents=True, exist_ok=True)
    historical = pd.read_parquet(args.processed_dir / "phase7a_candidate_history_panel.parquet")
    original = pd.read_parquet(args.processed_dir / "phase7b_phase7_evaluation_panel.parquet")
    inputs = {"additional_2023-01-03_2025-05-27": historical, "original_2025-05-28_2026-08-31": original}
    all_cells: list[pd.DataFrame] = []; all_formation: list[pd.DataFrame] = []; all_common: list[pd.DataFrame] = []
    all_summaries: list[dict] = []; all_ic: list[pd.DataFrame] = []; all_deciles: list[pd.DataFrame] = []; all_ls: list[pd.DataFrame] = []
    all_paired: list[pd.DataFrame] = []; all_paired_daily: list[pd.DataFrame] = []; all_rank_corr: list[pd.DataFrame] = []; all_dep: list[pd.DataFrame] = []; all_dep_daily: list[pd.DataFrame] = []; all_gl: list[pd.DataFrame] = []
    subperiod_rows = []
    for sample, panel in inputs.items():
        formation, cells = form_s2(panel, sample)
        # Target information is joined only after the formation-panel invariant has passed.
        target = panel[["Date", "canonical_research_symbol", "forward_oc_return", "target_available"]].copy()
        common = formation.merge(target, on=["Date", "canonical_research_symbol"], how="left", validate="one_to_one")
        common = common.loc[common["S0"].notna() & common["S1"].notna() & common["S2"].notna() & common["target_available"] & common["forward_oc_return"].notna()].copy()
        if common.empty or not common.groupby("Date").size().ge(10).all():
            raise AssertionError(f"Insufficient common daily cross-section for {sample}")
        common["sample"] = sample
        results, paired, paired_daily, rank_corr = evaluate_common(common, sample)
        dep, dep_daily = dependence_summary(common, sample)
        all_cells.append(cells); all_formation.append(formation); all_common.append(common)
        all_summaries.extend(result[4] for result in results.values())
        all_ic.extend(result[1] for result in results.values()); all_deciles.extend(result[2] for result in results.values()); all_ls.extend(result[3] for result in results.values())
        all_paired.append(paired); all_paired_daily.append(paired_daily); all_rank_corr.append(rank_corr); all_dep.append(dep); all_dep_daily.append(dep_daily); all_gl.append(globe_life_diagnostic(results, common, sample))
        if sample.startswith("original"):
            for name, start, end in ORIGINAL_SUBPERIODS:
                for signal, result in results.items():
                    values = result[1].loc[result[1].Date.between(start, end), "rank_ic"]
                    mean, se, t, p = hac_mean(values)
                    subperiod_rows.append({"sample": sample, "subperiod": name, "start": start, "end": end, "signal": signal, "days": len(values), "mean_ic": mean, "hac5_se": se, "hac5_t": t, "one_sided_hac_p_greater_zero": p})
    cells = pd.concat(all_cells, ignore_index=True); formation = pd.concat(all_formation, ignore_index=True); common = pd.concat(all_common, ignore_index=True)
    summary = pd.DataFrame(all_summaries); ic = pd.concat(all_ic, ignore_index=True); deciles = pd.concat(all_deciles, ignore_index=True); ls = pd.concat(all_ls, ignore_index=True)
    paired = pd.concat(all_paired, ignore_index=True); paired_daily = pd.concat(all_paired_daily, ignore_index=True); rank_corr = pd.concat(all_rank_corr, ignore_index=True); dependence = pd.concat(all_dep, ignore_index=True); dependence_daily = pd.concat(all_dep_daily, ignore_index=True); gl = pd.concat(all_gl, ignore_index=True)
    ic["rolling_60d_ic"] = ic.groupby(["sample", "signal"])["rank_ic"].transform(lambda values: values.rolling(60).mean())
    rank_summary = []
    for (sample, left, right), values in rank_corr.groupby(["sample", "left", "right"]):
        mean, se, t, p = hac_mean(values["rank_correlation"])
        rank_summary.append({"sample": sample, "left": left, "right": right, "mean_daily_rank_correlation": mean, "hac5_se": se, "hac5_t": t, "one_sided_hac_p_greater_zero": p, "days": len(values)})
    # Explicit common-sample coverage comparison; conditioning is allowed to remove only unavailable VS/VOL rows.
    coverage = formation.groupby("sample").agg(formation_stock_days=("Date", "size"), formation_dates=("Date", "nunique"), min_daily_formation=("Date", lambda values: values.value_counts().min()), max_daily_formation=("Date", lambda values: values.value_counts().max())).reset_index()
    common_counts = common.groupby("sample").agg(common_stock_days=("Date", "size"), common_dates=("Date", "nunique"), min_daily_common=("Date", lambda values: values.value_counts().min()), max_daily_common=("Date", lambda values: values.value_counts().max())).reset_index()
    s1_coverage_rows = []
    for sample, panel in inputs.items():
        start, end = SAMPLES[sample]
        s1_target = panel.loc[panel["Date"].between(start, end) & panel["universe_member"] & panel["S1"].notna() & panel["target_available"] & panel["forward_oc_return"].notna()]
        s1_coverage_rows.append({"sample": sample, "s1_target_stock_days": len(s1_target)})
    coverage = coverage.merge(common_counts, on="sample", validate="one_to_one").merge(pd.DataFrame(s1_coverage_rows), on="sample", validate="one_to_one")
    coverage["coverage_retained_from_formation"] = coverage.common_stock_days / coverage.formation_stock_days
    coverage["s2_formation_retained_from_s1"] = coverage.formation_stock_days / coverage.s1_target_stock_days
    coverage["s2_common_retained_from_s1"] = coverage.common_stock_days / coverage.s1_target_stock_days
    cell_summary = cells.groupby("sample").agg(cells=("cell_size", "size"), nonempty_days=("Date", "nunique"), mean_cell_size=("cell_size", "mean"), median_cell_size=("cell_size", "median"), min_cell_size=("cell_size", "min"), max_cell_size=("cell_size", "max"), small_cells_lt10=("small_cell_lt10", "sum"), small_cell_fraction=("small_cell_lt10", "mean")).reset_index()
    small_row_share = formation.assign(small_cell=formation.cell_size.lt(10)).groupby("sample", as_index=False).agg(small_cell_stock_day_fraction=("small_cell", "mean"))
    formation_ranks = formation.copy()
    formation_ranks["s2_rank"] = formation_ranks.groupby("Date")["S2"].rank(method="first")
    formation_ranks["s2_n"] = formation_ranks.groupby("Date")["S2"].transform("size")
    formation_ranks["s2_decile"] = np.floor((formation_ranks.s2_rank - 1) * 10 / formation_ranks.s2_n).astype(int) + 1
    small_extreme = formation_ranks.assign(small_cell=formation_ranks.cell_size.lt(10)).loc[lambda f: f.s2_decile.isin([1, 10])].groupby("sample", as_index=False).agg(small_cell_fraction_in_s2_extreme_deciles=("small_cell", "mean"))
    cell_summary = cell_summary.merge(small_row_share, on="sample", validate="one_to_one").merge(small_extreme, on="sample", validate="one_to_one")
    distribution_rows = []
    for sample, values in formation.groupby("sample"):
        for variable in ["z", "cell_median_z", "a", "S2"]:
            x = values[variable].dropna()
            distribution_rows.append({"sample": sample, "variable": variable, "n": len(x), "mean": x.mean(), "std": x.std(ddof=1), "min": x.min(), "p01": x.quantile(.01), "p50": x.median(), "p99": x.quantile(.99), "max": x.max()})
    # Persist all material audit objects.
    formation.to_parquet(args.processed_dir / "phase8_s2_formation_panel.parquet", index=False)
    common.to_parquet(args.processed_dir / "phase8_common_evaluation_panel.parquet", index=False)
    cells.to_csv(args.tables_dir / "phase8_state_cell_sizes.csv", index=False)
    cell_summary.to_csv(args.tables_dir / "phase8_state_cell_size_summary.csv", index=False)
    pd.DataFrame(distribution_rows).to_csv(args.tables_dir / "phase8_signal_distributions.csv", index=False)
    coverage.to_csv(args.tables_dir / "phase8_common_sample_coverage.csv", index=False)
    summary.to_csv(args.tables_dir / "phase8_common_sample_performance.csv", index=False)
    paired.to_csv(args.tables_dir / "phase8_paired_differences.csv", index=False)
    paired_daily.to_csv(args.tables_dir / "phase8_daily_paired_differences.csv", index=False)
    ic.to_csv(args.tables_dir / "phase8_daily_ic_and_rolling60.csv", index=False)
    deciles.to_csv(args.tables_dir / "phase8_decile_returns.csv", index=False)
    ls.to_csv(args.tables_dir / "phase8_daily_long_short.csv", index=False)
    grouped_results(ic, ls, "year").to_csv(args.tables_dir / "phase8_calendar_year_results.csv", index=False)
    pd.DataFrame(subperiod_rows).to_csv(args.tables_dir / "phase8_original_subperiod_results.csv", index=False)
    rank_corr.to_csv(args.tables_dir / "phase8_daily_signal_rank_correlations.csv", index=False)
    pd.DataFrame(rank_summary).to_csv(args.tables_dir / "phase8_signal_rank_correlation_summary.csv", index=False)
    dependence.to_csv(args.tables_dir / "phase8_dependence_summary.csv", index=False)
    dependence_daily.to_csv(args.tables_dir / "phase8_daily_dependence.csv", index=False)
    formation[["sample", "Date", "canonical_research_symbol", "z", "cell_median_z", "a", "S2", "cell_size", "vs_bucket", "vol_bucket", "state_cell"]].assign(abs_S2=lambda f: f.S2.abs()).sort_values("abs_S2", ascending=False).head(200).to_csv(args.tables_dir / "phase8_extreme_values.csv", index=False)
    gl.to_csv(args.tables_dir / "phase8_globe_life_diagnostic.csv", index=False)
    # Required concise figures, always separate by sample.
    for sample in SAMPLES:
        short = "additional" if sample.startswith("additional") else "original"
        plt.figure(figsize=(8, 4)); chart = cells.loc[cells["sample"].eq(sample)]
        plt.hist(chart.cell_size, bins=np.arange(chart.cell_size.min() - .5, chart.cell_size.max() + 1.5), color="#5077b8"); plt.axvline(10, color="#a83d3d", linestyle="--"); plt.xlabel("Daily state-cell size"); plt.ylabel("Cell-days"); plt.tight_layout(); plt.savefig(args.figures_dir / f"phase8_{short}_state_cell_sizes.png", dpi=150); plt.close()
        plt.figure(figsize=(8, 4))
        for signal, color in [("S1", "#2455a6"), ("S2", "#9b4d2b")]:
            chart = deciles.loc[(deciles["sample"] == sample) & (deciles["signal"] == signal)]
            plt.errorbar(chart.decile, chart.mean_return, yerr=1.96 * chart.hac5_se, fmt="o-", capsize=3, color=color, label=signal)
        plt.axhline(0, color="black", lw=.6); plt.xlabel("Decile"); plt.ylabel("Mean next-session O-C return"); plt.legend(); plt.tight_layout(); plt.savefig(args.figures_dir / f"phase8_{short}_s1_s2_deciles.png", dpi=150); plt.close()
        plt.figure(figsize=(9, 4))
        for signal, color in [("S0", "#777777"), ("S1", "#2455a6"), ("S2", "#9b4d2b")]:
            chart = ls.loc[(ls["sample"] == sample) & (ls["signal"] == signal)]
            plt.plot(chart.Date, (1 + chart.long_short).cumprod() - 1, color=color, label=signal)
        plt.axhline(0, color="black", lw=.6); plt.ylabel("Cumulative gross D10-D1"); plt.legend(); plt.tight_layout(); plt.savefig(args.figures_dir / f"phase8_{short}_cumulative.png", dpi=150); plt.close()
        plt.figure(figsize=(9, 4))
        for signal, color in [("S1", "#2455a6"), ("S2", "#9b4d2b")]:
            chart = ic.loc[(ic["sample"] == sample) & (ic["signal"] == signal)]
            plt.plot(chart.Date, chart.rolling_60d_ic, color=color, label=signal)
        plt.axhline(0, color="black", lw=.6); plt.ylabel("Rolling 60-day Rank IC"); plt.legend(); plt.tight_layout(); plt.savefig(args.figures_dir / f"phase8_{short}_s1_s2_rolling_ic.png", dpi=150); plt.close()
    plt.figure(figsize=(9, 4)); dep_chart = dependence.pivot(index=["sample", "variable"], columns="signal", values="mean_daily_spearman")
    dep_chart.plot(kind="bar", ax=plt.gca()); plt.axhline(0, color="black", lw=.6); plt.ylabel("Mean daily Spearman"); plt.xticks(rotation=25, ha="right"); plt.tight_layout(); plt.savefig(args.figures_dir / "phase8_dependence_before_after_conditioning.png", dpi=150); plt.close()
    decision = {}
    for sample in SAMPLES:
        s1 = summary.query("sample == @sample and signal == 'S1'").iloc[0]; s2 = summary.query("sample == @sample and signal == 'S2'").iloc[0]
        diff = paired.query("sample == @sample and comparison == 'S2_minus_S1'").iloc[0]
        # NOTE (2026-09-12): this reproduces the ORIGINAL two-sided |t| >= 2 primary
        # rule exactly, matching the checksum this file's output already carries in
        # the Phase 9/10/11 preservation manifests. The primary decision rule for
        # Rank-IC tests was amended to a one-sided t >= 1.645 bar on 2026-09-12; that
        # amendment is applied non-destructively by `apply_one_sided_ic_amendment_phase8.py`,
        # which writes a separate, clearly labeled output rather than changing this
        # pinned artifact. See `one_sided_ic_inference.py` and
        # `docs/one_sided_ic_inference_amendment_report.md`.
        decision[sample] = {"positive_s2_ic": bool(s2.mean_ic > 0), "s2_hac5_t_at_least_2": bool(s2.hac5_ic_t >= 2), "s2_minus_s1_ic_positive": bool(diff.mean_ic_difference > 0), "s2_decile_monotonicity_not_worse": bool(s2.decile_monotonic_spearman >= s1.decile_monotonic_spearman), "coverage_not_materially_reduced": bool(coverage.query("sample == @sample").iloc[0].s2_common_retained_from_s1 >= .99), "small_cell_fraction": float(cell_summary.query("sample == @sample").iloc[0].small_cell_fraction)}
    (args.tables_dir / "phase8_decision_rule_evaluation.json").write_text(json.dumps(decision, indent=2) + "\n")
    print(json.dumps({"common_sample_rows": coverage.to_dict(orient="records"), "decision": decision}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
