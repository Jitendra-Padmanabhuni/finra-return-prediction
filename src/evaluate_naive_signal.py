"""Phase 5 evaluation of raw FINRA q and S0=-q only; gross illustrative results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats


START, END, HAC_LAGS = "2025-05-28", "2026-08-31", 5


def hac_mean(series: pd.Series) -> tuple[float, float, float]:
    data = series.dropna().astype(float)
    fit = sm.OLS(data, np.ones((len(data), 1))).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})
    return float(fit.params[0]), float(fit.bse[0]), float(fit.tvalues[0])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--tables-dir", type=Path, default=Path("results/tables"))
    parser.add_argument("--figures-dir", type=Path, default=Path("results/figures"))
    args = parser.parse_args(); args.tables_dir.mkdir(parents=True, exist_ok=True); args.figures_dir.mkdir(parents=True, exist_ok=True)
    panel = pd.read_parquet(args.processed_dir / "master_stock_day_with_target.parquet")
    panel["Date"] = pd.to_datetime(panel["Date"])
    panel = panel.loc[panel.Date.between(START, END)].copy()
    panel["ShortVolume_numeric"] = pd.to_numeric(panel["ShortVolume"], errors="coerce")
    panel["TotalVolume_numeric"] = pd.to_numeric(panel["TotalVolume"], errors="coerce")
    valid_q = panel.finra_observation_present & panel.ShortVolume_numeric.notna() & panel.TotalVolume_numeric.gt(0)
    panel["q"] = np.where(valid_q, panel.ShortVolume_numeric / panel.TotalVolume_numeric, np.nan)
    tolerance = 1e-12
    if ((panel.q.dropna() < -tolerance) | (panel.q.dropna() > 1 + tolerance)).any(): raise ValueError("q outside [0,1] tolerance")
    panel["S0"] = -panel.q
    eligible = panel.q.notna() & panel.target_available & panel.forward_oc_return.notna()
    panel["naive_eligible"] = eligible
    panel["naive_exclusion_status"] = "eligible"
    panel.loc[panel.q.isna() & panel.target_available, "naive_exclusion_status"] = "missing_finra_ratio"
    panel.loc[panel.q.notna() & ~panel.target_available, "naive_exclusion_status"] = "missing_target"
    panel.loc[panel.q.isna() & ~panel.target_available, "naive_exclusion_status"] = "missing_finra_ratio_and_target"
    # Stable tie rule: canonical symbols ordered before ordinal first-rank, ascending S0.
    panel = panel.sort_values(["Date", "S0", "canonical_research_symbol"], na_position="last").copy()
    panel["s0_rank"] = panel.groupby("Date")["S0"].rank(method="first", ascending=True)
    panel["eligible_count_day"] = panel.groupby("Date")["naive_eligible"].transform("sum")
    panel["s0_decile"] = np.where(eligible, np.floor((panel.s0_rank - 1) * 10 / panel.eligible_count_day).astype("Int64") + 1, pd.NA)
    # rank must be over the eligible sample, not ratio-only rows with a missing target.
    panel.loc[~eligible, "s0_rank"] = np.nan
    panel.loc[~eligible, "s0_decile"] = pd.NA
    # redo ranks on the eligible sample to adhere to exact daily evaluation sample
    panel = panel.sort_values(["Date", "S0", "canonical_research_symbol"], na_position="last")
    panel.loc[eligible, "s0_rank"] = panel.loc[eligible].groupby("Date")["S0"].rank(method="first", ascending=True)
    panel.loc[eligible, "s0_decile"] = (np.floor((panel.loc[eligible,"s0_rank"] - 1) * 10 / panel.loc[eligible,"eligible_count_day"]).astype(int) + 1)
    daily_ic = panel.loc[eligible].groupby("Date").apply(lambda x: stats.spearmanr(x.S0, x.forward_oc_return).statistic, include_groups=False).rename("rank_ic").reset_index()
    ls = panel.loc[eligible].groupby(["Date", "s0_decile"], observed=True).forward_oc_return.mean().unstack("s0_decile")
    ls["d10_minus_d1"] = ls[10] - ls[1]
    ls = ls.reset_index()
    decile_daily = panel.loc[eligible].groupby(["Date", "s0_decile"], observed=True).forward_oc_return.mean().reset_index()
    decile_rows=[]
    for decile, group in decile_daily.groupby("s0_decile", observed=True):
        mean,se,t=hac_mean(group.forward_oc_return); decile_rows.append({"decile":int(decile),"mean_forward_oc_return":mean,"hac_se":se,"hac_t":t,"ci95_low":mean-1.96*se,"ci95_high":mean+1.96*se,"days":len(group)})
    deciles=pd.DataFrame(decile_rows).sort_values("decile")
    ic_mean,ic_se,ic_hac_t=hac_mean(daily_ic.rank_ic)
    ic_std=float(daily_ic.rank_ic.std(ddof=1)); ordinary_ic_t=float(stats.ttest_1samp(daily_ic.rank_ic,0).statistic)
    ls_mean,ls_se,ls_hac_t=hac_mean(ls.d10_minus_d1)
    ls_std=float(ls.d10_minus_d1.std(ddof=1)); ls_ordinary_t=float(stats.ttest_1samp(ls.d10_minus_d1,0).statistic)
    sub=[]
    for name,a,b in [("subperiod_1","2025-05-28","2026-01-13"),("subperiod_2","2026-01-14","2026-08-31")]:
        x=daily_ic.loc[daily_ic.Date.between(a,b),"rank_ic"]; sub.append({"subperiod":name,"start":a,"end":b,"days":len(x),"mean_rank_ic":x.mean(),"positive":bool(x.mean()>0)})
    sub=pd.DataFrame(sub)
    summary=pd.DataFrame([{"mean_rank_ic":ic_mean,"rank_ic_std":ic_std,"annualized_icir":ic_mean/ic_std*np.sqrt(252),"ordinary_ic_t":ordinary_ic_t,"hac5_ic_t":ic_hac_t,"positive_ic_day_fraction":float((daily_ic.rank_ic>0).mean()),"ls_mean_daily":ls_mean,"ls_annualized_arithmetic":ls_mean*252,"ls_annualized_volatility":ls_std*np.sqrt(252),"ls_sharpe":ls_mean/ls_std*np.sqrt(252),"ls_ordinary_t":ls_ordinary_t,"ls_hac5_t":ls_hac_t,"ls_cumulative_gross_return":float((1+ls.d10_minus_d1).prod()-1),"eligible_rows":int(eligible.sum()),"evaluation_rows":len(panel)}])
    exclusions=panel.groupby("naive_exclusion_status",as_index=False).size().rename(columns={"size":"rows"})
    daily_counts=panel.groupby("Date").agg(evaluation_rows=("Date","size"),eligible_rows=("naive_eligible","sum"),missing_q=("q",lambda s:s.isna().sum()),missing_target=("target_available",lambda s:(~s).sum()),daily_q_median=("q","median")).reset_index()
    q_nonmissing=panel.q.dropna()
    ratio_summary=pd.DataFrame([{"observations":len(q_nonmissing),"mean":q_nonmissing.mean(),"std":q_nonmissing.std(ddof=1),"min":q_nonmissing.min(),"p01":q_nonmissing.quantile(.01),"p05":q_nonmissing.quantile(.05),"p50":q_nonmissing.quantile(.50),"p95":q_nonmissing.quantile(.95),"p99":q_nonmissing.quantile(.99),"max":q_nonmissing.max()}])
    daily_distribution=panel.groupby("Date").q.agg(q_cross_sectional_mean="mean",q_cross_sectional_std="std",q_cross_sectional_median="median",q_p10=lambda s:s.quantile(.1),q_p90=lambda s:s.quantile(.9)).reset_index()
    panel.to_parquet(args.processed_dir / "master_stock_day_naive_signal.parquet",index=False)
    summary.to_csv(args.tables_dir/"phase5_naive_summary.csv",index=False); daily_ic.to_csv(args.tables_dir/"phase5_daily_rank_ic.csv",index=False); ls.to_csv(args.tables_dir/"phase5_daily_long_short.csv",index=False); deciles.to_csv(args.tables_dir/"phase5_decile_returns.csv",index=False); sub.to_csv(args.tables_dir/"phase5_rank_ic_subperiods.csv",index=False); exclusions.to_csv(args.tables_dir/"phase5_naive_exclusions.csv",index=False); daily_counts.to_csv(args.tables_dir/"phase5_daily_eligibility.csv",index=False)
    ratio_summary.to_csv(args.tables_dir/"phase5_ratio_distribution_summary.csv",index=False); daily_distribution.to_csv(args.tables_dir/"phase5_daily_ratio_distribution.csv",index=False)
    plt.figure(figsize=(8,4)); plt.hist(panel.q.dropna(),bins=80,color="#2455a6"); plt.xlabel("q = ShortVolume / TotalVolume"); plt.ylabel("Observations"); plt.tight_layout(); plt.savefig(args.figures_dir/"phase5_raw_ratio_distribution.png",dpi=150); plt.close()
    plt.figure(figsize=(9,4)); plt.plot(daily_counts.Date,daily_counts.daily_q_median,color="#2455a6"); plt.ylabel("Daily cross-sectional median q"); plt.tight_layout(); plt.savefig(args.figures_dir/"phase5_daily_median_ratio.png",dpi=150); plt.close()
    plt.figure(figsize=(7,4)); plt.errorbar(deciles.decile,deciles.mean_forward_oc_return,yerr=1.96*deciles.hac_se,fmt="o-",capsize=3,color="#2455a6"); plt.xlabel("S0 decile (10 = highest)"); plt.ylabel("Mean next-session O-C return"); plt.tight_layout(); plt.savefig(args.figures_dir/"phase5_decile_forward_returns.png",dpi=150); plt.close()
    ls["cumulative_gross"]=(1+ls.d10_minus_d1).cumprod()-1; plt.figure(figsize=(9,4)); plt.plot(ls.Date,ls.cumulative_gross,color="#2455a6"); plt.ylabel("Cumulative gross D10-D1 return"); plt.tight_layout(); plt.savefig(args.figures_dir/"phase5_cumulative_gross_long_short.png",dpi=150); plt.close()
    daily_ic["rolling_60d_ic"]=daily_ic.rank_ic.rolling(60).mean(); plt.figure(figsize=(9,4)); plt.plot(daily_ic.Date,daily_ic.rolling_60d_ic,color="#2455a6"); plt.axhline(0,color="black",lw=.7); plt.ylabel("60-day mean Rank IC"); plt.tight_layout(); plt.savefig(args.figures_dir/"phase5_rolling_60d_rank_ic.png",dpi=150); plt.close()
    print(json.dumps(summary.iloc[0].to_dict(),indent=2))

if __name__ == "__main__": main()
