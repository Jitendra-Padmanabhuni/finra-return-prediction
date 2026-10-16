"""Phase 6 associational confound analysis for the unchanged raw FINRA signal."""

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


START, END, HAC_LAGS = "2025-05-28", "2026-08-31", 5
SUBPERIODS = [("subperiod_1", "2025-05-28", "2026-01-13"), ("subperiod_2", "2026-01-14", "2026-08-31")]
VARIABLES = ["q", "S0", "same_day_oc_return", "reversal", "volume_surprise", "realized_volatility", "forward_oc_return"]


def hac_mean(series: pd.Series) -> tuple[float, float, float]:
    values = series.dropna().astype(float)
    fit = sm.OLS(values.to_numpy(), np.ones((len(values), 1))).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})
    return float(fit.params[0]), float(fit.bse[0]), float(fit.tvalues[0])


def rank_scaled(series: pd.Series) -> pd.Series:
    count = series.notna().sum()
    return 2 * (series.rank(method="average") - 0.5) / count - 1


def quintiles(frame: pd.DataFrame, feature: str) -> pd.Series:
    output = pd.Series(pd.NA, index=frame.index, dtype="Int64")
    for _, group in frame.loc[frame[feature].notna()].sort_values(["Date", feature, "canonical_research_symbol"]).groupby("Date"):
        ranks = group[feature].rank(method="first")
        output.loc[group.index] = (np.floor((ranks - 1) * 5 / len(group)).astype(int) + 1).astype("Int64")
    return output


def summarize_daily_cells(daily: pd.DataFrame, bucket: str, value: str) -> pd.DataFrame:
    rows = []
    for key, group in daily.groupby(bucket, observed=True):
        mean, se, tstat = hac_mean(group[value])
        rows.append({bucket: int(key), "metric": value, "mean": mean, "hac5_se": se, "hac5_t": tstat, "days": len(group)})
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--tables-dir", type=Path, default=Path("results/tables"))
    parser.add_argument("--figures-dir", type=Path, default=Path("results/figures"))
    args = parser.parse_args(); args.tables_dir.mkdir(parents=True, exist_ok=True); args.figures_dir.mkdir(parents=True, exist_ok=True)
    panel = pd.read_parquet(args.processed_dir / "master_stock_day_with_target.parquet").sort_values(["canonical_research_symbol", "Date"])
    panel["ShortVolume_numeric"] = pd.to_numeric(panel.ShortVolume, errors="coerce")
    panel["TotalVolume_numeric"] = pd.to_numeric(panel.TotalVolume, errors="coerce")
    panel["q"] = np.where(panel.finra_observation_present & panel.TotalVolume_numeric.gt(0), panel.ShortVolume_numeric / panel.TotalVolume_numeric, np.nan)
    panel["S0"] = -panel.q
    valid_price = panel.adjusted_open.gt(0) & panel.adjusted_close.gt(0)
    panel["same_day_oc_return"] = np.where(valid_price, panel.adjusted_close / panel.adjusted_open - 1, np.nan)
    panel["reversal"] = -panel.same_day_oc_return
    grouped = panel.groupby("canonical_research_symbol", sort=False)
    panel["prior_volume_median_20"] = grouped.Volume.transform(lambda s: s.shift(1).rolling(20, min_periods=20).median())
    panel["volume_surprise"] = np.where(panel.Volume.gt(0) & panel.prior_volume_median_20.gt(0), np.log(panel.Volume / panel.prior_volume_median_20), np.nan)
    panel["close_to_close_return"] = grouped.adjusted_close.transform(lambda s: s / s.shift(1) - 1)
    panel["realized_volatility"] = panel.groupby("canonical_research_symbol", sort=False).close_to_close_return.transform(lambda s: s.shift(1).rolling(20, min_periods=20).std(ddof=1))
    evaluation = panel.loc[panel.Date.between(START, END)].copy()

    corr_daily_rows = []
    for date, day in evaluation.groupby("Date"):
        for left, right in itertools.combinations(VARIABLES, 2):
            pair = day[[left, right]].dropna()
            value = stats.spearmanr(pair[left], pair[right]).statistic if len(pair) >= 10 and pair[left].nunique() > 1 and pair[right].nunique() > 1 else np.nan
            corr_daily_rows.append({"Date": date, "variable_1": left, "variable_2": right, "spearman": value, "observations": len(pair)})
    corr_daily = pd.DataFrame(corr_daily_rows)
    corr_summary_rows = []
    for (left, right), group in corr_daily.groupby(["variable_1", "variable_2"]):
        mean, se, tstat = hac_mean(group.spearman)
        corr_summary_rows.append({"variable_1": left, "variable_2": right, "mean_daily_spearman": mean, "hac5_se": se, "hac5_t": tstat, "positive_day_fraction": (group.spearman > 0).mean(), "same_sign_day_fraction": ((group.spearman > 0) if mean >= 0 else (group.spearman < 0)).mean(), "days": group.spearman.notna().sum()})
    corr_summary = pd.DataFrame(corr_summary_rows)
    corr_subperiod_rows = []
    for name, start, end in SUBPERIODS:
        for (left, right), group in corr_daily.loc[corr_daily.Date.between(start, end)].groupby(["variable_1", "variable_2"]):
            mean, se, tstat = hac_mean(group.spearman)
            corr_subperiod_rows.append({"subperiod": name, "start": start, "end": end, "variable_1": left, "variable_2": right, "mean_daily_spearman": mean, "hac5_t": tstat, "days": group.spearman.notna().sum()})
    corr_subperiod = pd.DataFrame(corr_subperiod_rows)

    quintile_summaries = []
    for feature, bucket in [("same_day_oc_return", "same_day_return_quintile"), ("volume_surprise", "volume_surprise_quintile"), ("realized_volatility", "realized_volatility_quintile")]:
        evaluation[bucket] = quintiles(evaluation, feature)
        metrics = ["q", "S0", "forward_oc_return"] if feature == "same_day_oc_return" else ["q"]
        daily = evaluation.groupby(["Date", bucket], observed=True)[metrics].mean().reset_index()
        for metric in metrics:
            result = summarize_daily_cells(daily, bucket, metric); result["sort_feature"] = feature; quintile_summaries.append(result.rename(columns={bucket: "quintile"}))
        if feature == "same_day_oc_return":
            ic_rows=[]
            for (date, qtile), group in evaluation.groupby(["Date", bucket], observed=True):
                x=group[["S0","forward_oc_return"]].dropna()
                ic=stats.spearmanr(x.S0,x.forward_oc_return).statistic if len(x)>=10 and x.S0.nunique()>1 else np.nan
                ic_rows.append({"Date":date,"quintile":int(qtile),"within_quintile_s0_ic":ic})
            ic_daily=pd.DataFrame(ic_rows)
            result=summarize_daily_cells(ic_daily,"quintile","within_quintile_s0_ic"); result["sort_feature"]=feature; quintile_summaries.append(result)
    quintile_summary = pd.concat(quintile_summaries, ignore_index=True)

    common_vars = ["forward_oc_return", "S0", "reversal", "volume_surprise", "realized_volatility"]
    common = evaluation.dropna(subset=common_vars).copy()
    for variable in common_vars[1:]: common[f"rank_{variable}"] = common.groupby("Date")[variable].transform(rank_scaled)
    specifications = {"model_1_s0": ["rank_S0"], "model_2_s0_reversal": ["rank_S0", "rank_reversal"], "model_3_all_controls": ["rank_S0", "rank_reversal", "rank_volume_surprise", "rank_realized_volatility"]}
    coefficient_rows=[]
    for date, day in common.groupby("Date"):
        for model, predictors in specifications.items():
            fit=sm.OLS(day.forward_oc_return.astype(float), sm.add_constant(day[predictors].astype(float), has_constant="add")).fit()
            for parameter, value in fit.params.items(): coefficient_rows.append({"Date":date,"model":model,"coefficient":parameter,"value":value,"observations":len(day)})
    coefficients=pd.DataFrame(coefficient_rows)
    coefficient_summary_rows=[]
    for (model, coefficient), group in coefficients.groupby(["model","coefficient"]):
        mean,se,tstat=hac_mean(group.value); coefficient_summary_rows.append({"model":model,"coefficient":coefficient,"mean_coefficient":mean,"hac5_se":se,"hac5_t":tstat,"days":len(group),"mean_daily_observations":group.observations.mean()})
    coefficient_summary=pd.DataFrame(coefficient_summary_rows)

    evaluation.to_parquet(args.processed_dir/"phase6_confound_panel.parquet",index=False)
    corr_daily.to_csv(args.tables_dir/"phase6_daily_correlations.csv",index=False); corr_summary.to_csv(args.tables_dir/"phase6_correlation_summary.csv",index=False); corr_subperiod.to_csv(args.tables_dir/"phase6_correlation_subperiods.csv",index=False); quintile_summary.to_csv(args.tables_dir/"phase6_quintile_summary.csv",index=False); coefficients.to_csv(args.tables_dir/"phase6_daily_regression_coefficients.csv",index=False); coefficient_summary.to_csv(args.tables_dir/"phase6_regression_summary.csv",index=False)

    def qplot(feature, filename, label):
        d=quintile_summary.query("sort_feature==@feature and metric=='q'").sort_values("quintile"); plt.figure(figsize=(6,4)); plt.errorbar(d.quintile,d["mean"],yerr=1.96*d.hac5_se,fmt="o-",capsize=3); plt.xlabel(label); plt.ylabel("Mean q"); plt.tight_layout(); plt.savefig(args.figures_dir/filename,dpi=150); plt.close()
    qplot("same_day_oc_return","phase6_q_by_same_day_return_quintile.png","Same-day return quintile")
    qplot("volume_surprise","phase6_q_by_volume_surprise_quintile.png","Volume-surprise quintile")
    qplot("realized_volatility","phase6_q_by_realized_volatility_quintile.png","Prior realized-volatility quintile")
    s0=coefficient_summary.query("coefficient=='rank_S0'").copy(); plt.figure(figsize=(7,4)); plt.errorbar(range(len(s0)),s0.mean_coefficient,yerr=1.96*s0.hac5_se,fmt="o",capsize=3); plt.xticks(range(len(s0)),["S0","+ reversal","+ reversal, volume, vol"]); plt.axhline(0,color="black",lw=.7); plt.ylabel("Mean daily S0 coefficient"); plt.tight_layout(); plt.savefig(args.figures_dir/"phase6_s0_coefficient_by_model.png",dpi=150); plt.close()
    selected=[("q","same_day_oc_return"),("q","volume_surprise"),("q","realized_volatility")]; stable=corr_subperiod.set_index(["variable_1","variable_2"]).loc[selected].reset_index(); pivot=stable.pivot(index=["variable_1","variable_2"],columns="subperiod",values="mean_daily_spearman"); pivot.plot(kind="bar",figsize=(8,4)); plt.ylabel("Mean daily Spearman"); plt.xticks(rotation=20,ha="right"); plt.tight_layout(); plt.savefig(args.figures_dir/"phase6_confound_correlations_by_subperiod.png",dpi=150); plt.close()
    print(json.dumps({"common_regression_rows":len(common),"common_regression_days":common.Date.nunique()},indent=2))

if __name__ == "__main__": main()
