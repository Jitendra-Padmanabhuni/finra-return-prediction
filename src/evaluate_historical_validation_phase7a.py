"""Evaluate frozen S0/S1 on Phase 7A without pooling incompatible universes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from evaluate_candidate_history_phase7b import hac_mean, signal_eval


HIST_START, HIST_END = "2023-01-03", "2025-05-27"
ORIG_START, ORIG_END = "2025-05-28", "2026-08-31"
ORIGINAL_SUBPERIODS = [
    ("subperiod_1", "2025-05-28", "2026-01-13"),
    ("subperiod_2", "2026-01-14", "2026-08-31"),
]


def max_drawdown(returns: pd.Series) -> float:
    wealth = (1 + returns.fillna(0)).cumprod()
    running_peak = wealth.cummax()
    return float((wealth / running_peak - 1).min())


def add_summary_fields(summary: dict[str, float], long_short: pd.DataFrame, rows: int) -> dict[str, float]:
    output = dict(summary)
    output["eligible_stock_days"] = rows
    output["ls_max_drawdown"] = max_drawdown(long_short["long_short"])
    return output


def evaluate_period(frame: pd.DataFrame, period: str):
    eligible_s0 = frame.loc[frame["q"].notna() & frame["target_available"] & frame["forward_oc_return"].notna()].copy()
    paired = frame.loc[frame["S1"].notna() & frame["target_available"] & frame["forward_oc_return"].notna()].copy()
    evaluated = {}
    for label, sample, signal in [("S0_full", eligible_s0, "S0"), ("S0_paired", paired, "S0"), ("S1", paired, "S1")]:
        _, ic, deciles, long_short, summary = signal_eval(sample, signal)
        summary = add_summary_fields(summary, long_short, len(sample))
        summary.update({"period": period, "signal": label})
        ic = ic.assign(period=period, signal=label)
        deciles = deciles.assign(period=period, signal=label)
        long_short = long_short.assign(period=period, signal=label)
        evaluated[label] = (ic, deciles, long_short, summary)

    s0_ic, s0_ls = evaluated["S0_paired"][0], evaluated["S0_paired"][2]
    s1_ic, s1_ls = evaluated["S1"][0], evaluated["S1"][2]
    ic_pair = s1_ic[["Date", "rank_ic"]].merge(s0_ic[["Date", "rank_ic"]], on="Date", suffixes=("_s1", "_s0"), validate="one_to_one")
    ic_pair["difference"] = ic_pair["rank_ic_s1"] - ic_pair["rank_ic_s0"]
    ls_pair = s1_ls[["Date", "long_short"]].merge(s0_ls[["Date", "long_short"]], on="Date", suffixes=("_s1", "_s0"), validate="one_to_one")
    ls_pair["difference"] = ls_pair["long_short_s1"] - ls_pair["long_short_s0"]
    ic_mean, ic_se, ic_t, ic_p = hac_mean(ic_pair["difference"])
    ls_mean, ls_se, ls_t, ls_p = hac_mean(ls_pair["difference"])
    paired_summary = {
        "period": period,
        "mean_ic_difference_s1_minus_s0": ic_mean,
        "hac5_ic_difference_se": ic_se,
        "hac5_ic_difference_t": ic_t,
        "one_sided_hac_ic_difference_p_greater_zero": ic_p,
        "mean_long_short_difference_s1_minus_s0": ls_mean,
        "hac5_long_short_difference_se": ls_se,
        "hac5_long_short_difference_t": ls_t,
        "one_sided_hac_long_short_difference_p_greater_zero": ls_p,
    }
    return evaluated, paired_summary, ic_pair.assign(period=period), ls_pair.assign(period=period)


def grouped_performance(ic: pd.DataFrame, ls: pd.DataFrame, frequency: str) -> pd.DataFrame:
    keyed_ic = ic.copy(); keyed_ls = ls.copy()
    if frequency == "year":
        keyed_ic["group"] = keyed_ic["Date"].dt.year.astype(str)
        keyed_ls["group"] = keyed_ls["Date"].dt.year.astype(str)
    else:
        keyed_ic["group"] = keyed_ic["Date"].dt.to_period("M").astype(str)
        keyed_ls["group"] = keyed_ls["Date"].dt.to_period("M").astype(str)
    rows = []
    for (period, signal, group), values in keyed_ic.groupby(["period", "signal", "group"]):
        ls_values = keyed_ls.loc[(keyed_ls.period == period) & (keyed_ls.signal == signal) & (keyed_ls.group == group), "long_short"]
        ic_mean, ic_se, ic_t, ic_p = hac_mean(values["rank_ic"])
        ls_mean, ls_se, ls_t, ls_p = hac_mean(ls_values)
        ls_std = ls_values.std(ddof=1)
        rows.append({"period": period, "signal": signal, frequency: group, "days": len(values), "mean_ic": ic_mean, "hac5_ic_se": ic_se, "hac5_ic_t": ic_t, "one_sided_hac_ic_p_greater_zero": ic_p, "positive_ic_fraction": (values.rank_ic > 0).mean(), "ls_mean": ls_mean, "hac5_ls_se": ls_se, "hac5_ls_t": ls_t, "one_sided_hac_ls_p_greater_zero": ls_p, "ls_sharpe_annualized": ls_mean / ls_std * np.sqrt(252) if ls_std > 0 else np.nan, "ls_cumulative_gross": (1 + ls_values).prod() - 1, "ls_max_drawdown": max_drawdown(ls_values)})
    return pd.DataFrame(rows)


def assert_original_replication(evaluated: dict, tables_dir: Path) -> pd.DataFrame:
    checks = []
    references = {
        ("S0_paired", "ic"): "phase7b_phase7_daily_ic_s0_paired.csv",
        ("S1", "ic"): "phase7b_phase7_daily_ic_s1.csv",
        ("S0_paired", "ls"): "phase7b_phase7_daily_ls_s0_paired.csv",
        ("S1", "ls"): "phase7b_phase7_daily_ls_s1.csv",
    }
    for (signal, kind), filename in references.items():
        candidate = evaluated[signal][0 if kind == "ic" else 2]
        value = "rank_ic" if kind == "ic" else "long_short"
        reference = pd.read_csv(tables_dir / filename, parse_dates=["Date"])
        merged = candidate[["Date", value]].merge(reference[["Date", value]], on="Date", suffixes=("_new", "_reference"), validate="one_to_one")
        maximum = float((merged[f"{value}_new"] - merged[f"{value}_reference"]).abs().max())
        passed = len(merged) == len(reference) == len(candidate) and maximum <= 1e-15
        checks.append({"signal": signal, "series": kind, "rows": len(merged), "maximum_absolute_difference": maximum, "exact_within_1e_15": passed})
    output = pd.DataFrame(checks)
    if not output["exact_within_1e_15"].all():
        raise AssertionError("Original Phase 7B daily series did not reproduce")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--tables-dir", type=Path, default=Path("results/tables"))
    parser.add_argument("--figures-dir", type=Path, default=Path("results/figures"))
    args = parser.parse_args(); args.figures_dir.mkdir(parents=True, exist_ok=True)
    gate = json.loads((args.processed_dir / "phase7a_coverage_gate.json").read_text())
    if not gate["coverage_gate_pass"]:
        raise RuntimeError("Phase 7A coverage gate failed; performance is prohibited")

    historical = pd.read_parquet(args.processed_dir / "phase7a_candidate_history_panel.parquet")
    historical = historical.loc[historical["Date"].between(HIST_START, HIST_END) & historical["universe_member"]].copy()
    original = pd.read_parquet(args.processed_dir / "phase7b_phase7_evaluation_panel.parquet")
    original = original.loc[original["Date"].between(ORIG_START, ORIG_END) & original["universe_member"]].copy()
    if not historical.groupby("Date").size().eq(400).all() or historical["Date"].nunique() != 601:
        raise AssertionError("Historical evaluation does not contain 400 members on 601 dates")
    if not original.groupby("Date").size().eq(400).all() or original["Date"].nunique() != 317:
        raise AssertionError("Original evaluation membership changed")

    for frame, period in [(historical, "additional_2023-01-03_2025-05-27"), (original, "original_2025-05-28_2026-08-31")]:
        frame["s1_eligibility_status"] = "eligible"
        frame.loc[frame["q"].isna(), "s1_eligibility_status"] = "current_q_missing"
        frame.loc[frame["q"].notna() & ~frame["exact_60_valid_history"], "s1_eligibility_status"] = "missing_exact_60_q_history"
        frame.loc[frame["S1"].notna() & ~frame["target_available"], "s1_eligibility_status"] = "missing_target"
        frame["period"] = period

    orig_eval, orig_pair, orig_ic_diff, orig_ls_diff = evaluate_period(original, "original_2025-05-28_2026-08-31")
    replication = assert_original_replication(orig_eval, args.tables_dir)
    replication.to_csv(args.tables_dir / "phase7a_original_replication_validation.csv", index=False)

    # Only after exact original reproduction succeeds do we evaluate the new data.
    hist_eval, hist_pair, hist_ic_diff, hist_ls_diff = evaluate_period(historical, "additional_2023-01-03_2025-05-27")
    all_eval = [orig_eval, hist_eval]
    summaries = pd.DataFrame([value[3] for evaluated in all_eval for value in evaluated.values()])
    paired = pd.DataFrame([orig_pair, hist_pair])
    daily_ic = pd.concat([value[0] for evaluated in all_eval for value in evaluated.values()], ignore_index=True)
    deciles = pd.concat([value[1] for evaluated in all_eval for value in evaluated.values()], ignore_index=True)
    daily_ls = pd.concat([value[2] for evaluated in all_eval for value in evaluated.values()], ignore_index=True)
    daily_ic["rolling_60d_ic"] = daily_ic.groupby(["period", "signal"])["rank_ic"].transform(lambda series: series.rolling(60).mean())

    sub_rows = []
    for name, start, end in ORIGINAL_SUBPERIODS:
        for signal, value in orig_eval.items():
            values = value[0].loc[value[0]["Date"].between(start, end), "rank_ic"]
            mean, se, t, p = hac_mean(values)
            sub_rows.append({"subperiod": name, "start": start, "end": end, "signal": signal, "days": len(values), "mean_ic": mean, "hac5_se": se, "hac5_t": t, "one_sided_hac_p_greater_zero": p})

    summaries.to_csv(args.tables_dir / "phase7a_performance_summary.csv", index=False)
    paired.to_csv(args.tables_dir / "phase7a_paired_differences.csv", index=False)
    daily_ic.to_csv(args.tables_dir / "phase7a_daily_ic_and_rolling60.csv", index=False)
    daily_ls.to_csv(args.tables_dir / "phase7a_daily_long_short.csv", index=False)
    deciles.to_csv(args.tables_dir / "phase7a_decile_returns.csv", index=False)
    pd.concat([orig_ic_diff, hist_ic_diff]).to_csv(args.tables_dir / "phase7a_daily_paired_ic_differences.csv", index=False)
    pd.concat([orig_ls_diff, hist_ls_diff]).to_csv(args.tables_dir / "phase7a_daily_paired_long_short_differences.csv", index=False)
    pd.DataFrame(sub_rows).to_csv(args.tables_dir / "phase7a_original_subperiod_results.csv", index=False)
    grouped_performance(daily_ic, daily_ls, "year").to_csv(args.tables_dir / "phase7a_calendar_year_results.csv", index=False)
    grouped_performance(daily_ic, daily_ls, "month").to_csv(args.tables_dir / "phase7a_monthly_results.csv", index=False)
    eligibility_frames = []
    for frame in [historical, original]:
        eligibility_frames.append(frame.groupby(["period", "s1_eligibility_status"], as_index=False).size().rename(columns={"size": "stock_days"}))
    pd.concat(eligibility_frames, ignore_index=True).to_csv(args.tables_dir / "phase7a_s1_eligibility_summary.csv", index=False)
    historical.groupby("Date").agg(top400_rows=("Date", "size"), s0_eligible=("q", lambda values: values.notna().sum()), s1_eligible=("S1", lambda values: values.notna().sum()), target_available=("target_available", "sum")).reset_index().to_csv(args.tables_dir / "phase7a_historical_daily_eligibility.csv", index=False)
    historical.groupby(["canonical_research_symbol", "source_symbol"], as_index=False).agg(top400_days=("Date", "size"), s0_eligible=("q", lambda values: values.notna().sum()), s1_eligible=("S1", lambda values: values.notna().sum()), target_available=("target_available", "sum")).to_csv(args.tables_dir / "phase7a_historical_security_eligibility.csv", index=False)

    for period, color in [("additional_2023-01-03_2025-05-27", "#2455a6"), ("original_2025-05-28_2026-08-31", "#9b4d2b")]:
        plt.figure(figsize=(8, 4))
        for signal, style in [("S0_paired", "--"), ("S1", "-")]:
            chart = daily_ic.query("period == @period and signal == @signal")
            plt.plot(chart.Date, chart.rolling_60d_ic, linestyle=style, color=color, label=signal)
        plt.axhline(0, color="black", lw=.6); plt.ylabel("Rolling 60-day Rank IC"); plt.legend(); plt.tight_layout()
        short = "additional" if period.startswith("additional") else "original"
        plt.savefig(args.figures_dir / f"phase7a_{short}_rolling60_ic.png", dpi=150); plt.close()
    plt.figure(figsize=(9, 4))
    for period, color in [("additional_2023-01-03_2025-05-27", "#2455a6"), ("original_2025-05-28_2026-08-31", "#9b4d2b")]:
        chart = daily_ls.query("period == @period and signal == 'S1'").copy()
        plt.plot(chart.Date, (1 + chart.long_short).cumprod() - 1, color=color, label=period.split("_")[0])
    plt.axhline(0, color="black", lw=.6); plt.ylabel("S1 cumulative gross D10-D1"); plt.legend(); plt.tight_layout(); plt.savefig(args.figures_dir / "phase7a_s1_cumulative_by_period.png", dpi=150); plt.close()
    plt.figure(figsize=(9, 4))
    for (period, signal), chart in deciles.groupby(["period", "signal"]):
        if signal not in {"S0_paired", "S1"}: continue
        plt.plot(chart.decile, chart.mean_return, marker="o", label=f"{period.split('_')[0]} {signal}")
    plt.axhline(0, color="black", lw=.6); plt.xlabel("Decile"); plt.ylabel("Mean next-session O-C return"); plt.legend(ncol=2); plt.tight_layout(); plt.savefig(args.figures_dir / "phase7a_decile_comparison.png", dpi=150); plt.close()
    print(summaries[["period", "signal", "mean_ic", "hac5_ic_t", "ls_sharpe", "eligible_stock_days"]].to_json(orient="records", indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
