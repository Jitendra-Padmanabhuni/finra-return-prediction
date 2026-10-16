"""Phase 7 fixed 60-date stock-relative FINRA anomaly and paired S0 comparison."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

START, END, W, EPS, HAC = "2025-05-28", "2026-08-31", 60, 0.000001, 5
SUBS=[("subperiod_1","2025-05-28","2026-01-13"),("subperiod_2","2026-01-14","2026-08-31")]
def hac(s):
    x=s.dropna().astype(float).to_numpy(); f=sm.OLS(x,np.ones((len(x),1))).fit(cov_type="HAC",cov_kwds={"maxlags":HAC}); return float(f.params[0]),float(f.bse[0]),float(f.tvalues[0])
def mad(a):
    m=np.median(a); return np.median(np.abs(a-m))
def signal_eval(frame, signal):
    x=frame[["Date","canonical_research_symbol","forward_oc_return",signal]].dropna().sort_values(["Date",signal,"canonical_research_symbol"]).copy()
    x["rank"]=x.groupby("Date")[signal].rank(method="first")
    x["n"]=x.groupby("Date")[signal].transform("size")
    x["decile"]=(np.floor((x["rank"]-1)*10/x["n"]).astype(int)+1)
    ic=x.groupby("Date").apply(lambda g:stats.spearmanr(g[signal],g.forward_oc_return).statistic,include_groups=False).rename("rank_ic").reset_index()
    dec_daily=x.groupby(["Date","decile"],observed=True).forward_oc_return.mean().reset_index()
    dec=[]
    for d,g in dec_daily.groupby("decile",observed=True):
        m,se,t=hac(g.forward_oc_return);dec.append({"decile":int(d),"mean_return":m,"hac5_se":se,"hac5_t":t,"days":len(g)})
    dec=pd.DataFrame(dec).sort_values("decile")
    ls=dec_daily.pivot(index="Date",columns="decile",values="forward_oc_return");ls["long_short"]=ls[10]-ls[1];ls=ls.reset_index()
    m,se,t=hac(ic.rank_ic); std=ic.rank_ic.std(ddof=1)
    lm,lse,lt=hac(ls.long_short); lstd=ls.long_short.std(ddof=1)
    mono=stats.spearmanr(dec.decile,dec.mean_return).statistic
    summary={"mean_ic":m,"hac5_ic_t":t,"ic_std":std,"annualized_icir":m/std*np.sqrt(252),"positive_ic_fraction":float((ic.rank_ic>0).mean()),"ls_mean":lm,"ls_hac5_t":lt,"ls_annualized_arithmetic":lm*252,"ls_annualized_volatility":lstd*np.sqrt(252),"ls_sharpe":lm/lstd*np.sqrt(252),"ls_cumulative_gross":float((1+ls.long_short).prod()-1),"decile_monotonic_spearman":mono,"decile_nonnegative_steps":int((dec.mean_return.diff().dropna()>=0).sum()),"days":len(ic)}
    return x,ic,dec,ls,summary
def main():
 p=argparse.ArgumentParser();p.add_argument("--processed-dir",type=Path,default=Path("data/processed"));p.add_argument("--tables-dir",type=Path,default=Path("results/tables"));p.add_argument("--figures-dir",type=Path,default=Path("results/figures"));a=p.parse_args();a.tables_dir.mkdir(parents=True,exist_ok=True);a.figures_dir.mkdir(parents=True,exist_ok=True)
 panel=pd.read_parquet(a.processed_dir/"master_stock_day_with_target.parquet");panel["Date"]=pd.to_datetime(panel.Date);panel["q"]=np.where(panel.finra_observation_present & pd.to_numeric(panel.TotalVolume,errors="coerce").gt(0),pd.to_numeric(panel.ShortVolume,errors="coerce")/pd.to_numeric(panel.TotalVolume,errors="coerce"),np.nan);panel["S0"]=-panel.q
 dates=pd.DatetimeIndex(sorted(panel.Date.unique()));syms=sorted(panel.canonical_research_symbol.unique());idx=pd.MultiIndex.from_product([dates,syms],names=["Date","canonical_research_symbol"])
 raw=panel.set_index(["Date","canonical_research_symbol"]);q=raw.q.reindex(idx);present=pd.Series(idx.isin(raw.index),index=idx)
 hist_med=q.groupby(level=1).transform(lambda s:s.shift(1).rolling(W,min_periods=W).median()); hist_mad=q.groupby(level=1).transform(lambda s:s.shift(1).rolling(W,min_periods=W).apply(mad,raw=True)); qcount=q.notna().groupby(level=1).transform(lambda s:s.shift(1).rolling(W,min_periods=W).sum()); pcount=present.groupby(level=1).transform(lambda s:s.shift(1).rolling(W,min_periods=W).sum())
 hist=pd.DataFrame({"historical_median":hist_med,"historical_mad":hist_mad,"prior_valid_q_count":qcount,"prior_present_count":pcount}).reset_index()
 panel=panel.merge(hist,on=["Date","canonical_research_symbol"],how="left",validate="one_to_one");panel["exact_60_valid_history"]=panel.prior_valid_q_count.eq(W);panel["interrupted_universe_history"]=panel.prior_present_count.lt(W);panel["missing_finra_history"]=panel.prior_present_count.eq(W)&panel.prior_valid_q_count.lt(W);panel["near_zero_mad"]=panel.historical_mad.le(EPS);panel["z"]=np.where(panel.q.notna()&panel.exact_60_valid_history,(panel.q-panel.historical_median)/(1.4826*panel.historical_mad+EPS),np.nan);panel["S1"]=-panel.z
 ev=panel.loc[panel.Date.between(START,END)].copy();ev["s1_eligible"]=ev.S1.notna()&ev.target_available&ev.forward_oc_return.notna();ev["s1_status"]="eligible";ev.loc[ev.q.isna(),"s1_status"]="current_q_missing";ev.loc[ev.q.notna()&ev.interrupted_universe_history,"s1_status"]="interrupted_universe_history";ev.loc[ev.q.notna()&~ev.interrupted_universe_history&ev.missing_finra_history,"s1_status"]="missing_finra_history";ev.loc[ev.S1.notna()&~ev.target_available,"s1_status"]="missing_target";ev.loc[ev.s1_eligible,"s1_status"]="eligible"
 paired=ev.loc[ev.s1_eligible].copy();s0x,s0ic,s0dec,s0ls,s0sum=signal_eval(paired,"S0");s1x,s1ic,s1dec,s1ls,s1sum=signal_eval(paired,"S1")
 icpair=s1ic.merge(s0ic,on="Date",suffixes=("_s1","_s0"));icpair["ic_difference"]=icpair.rank_ic_s1-icpair.rank_ic_s0;ls_pair=s1ls.merge(s0ls,on="Date",suffixes=("_s1","_s0"));ls_pair["long_short_difference"]=ls_pair.long_short_s1-ls_pair.long_short_s0
 dm,dse,dt=hac(icpair.ic_difference);lm,lse,lt=hac(ls_pair.long_short_difference)
 rankcorr=paired.groupby("Date").apply(lambda g:stats.spearmanr(g.S0,g.S1).statistic,include_groups=False).rename("s0_s1_rank_correlation").reset_index();rcm,rcse,rct=hac(rankcorr.s0_s1_rank_correlation)
 subs=[]
 for name,start,end in SUBS:
  for sig,ic in [("S0",s0ic),("S1",s1ic)]:
   v=ic.loc[ic.Date.between(start,end),"rank_ic"];subs.append({"signal":sig,"subperiod":name,"start":start,"end":end,"days":len(v),"mean_ic":v.mean(),"hac5_t":hac(v)[2]})
 summary=pd.DataFrame([{**{"signal":"S0_paired"},**s0sum},{**{"signal":"S1"},**s1sum}]);paired_summary=pd.DataFrame([{"mean_ic_difference_s1_minus_s0":dm,"hac5_ic_difference_t":dt,"mean_long_short_difference_s1_minus_s0":lm,"hac5_long_short_difference_t":lt,"mean_daily_s0_s1_rank_correlation":rcm,"hac5_rank_correlation_t":rct}])
 eligibility=ev.groupby("s1_status",as_index=False).size().rename(columns={"size":"rows"});daily_elig=ev.groupby("Date").agg(rows=("Date","size"),eligible=("s1_eligible","sum"),current_q_missing=("q",lambda s:s.isna().sum()),interrupted_universe_history=("interrupted_universe_history","sum"),missing_finra_history=("missing_finra_history","sum"),near_zero_mad=("near_zero_mad","sum")).reset_index();sec_elig=ev.groupby("canonical_research_symbol").agg(rows=("Date","size"),eligible=("s1_eligible","sum"),interrupted_universe_history=("interrupted_universe_history","sum"),missing_finra_history=("missing_finra_history","sum")).reset_index()
 dist=[]
 for col in ["historical_median","historical_mad","z","S1"]:
  v=ev[col].dropna();dist.append({"variable":col,"n":len(v),"mean":v.mean(),"std":v.std(ddof=1),"min":v.min(),"p01":v.quantile(.01),"p50":v.median(),"p99":v.quantile(.99),"max":v.max()})
 extreme=ev.loc[ev.z.notna(),["Date","canonical_research_symbol","q","historical_median","historical_mad","z","S1","near_zero_mad","forward_oc_return"]].assign(abs_z=lambda x:x.z.abs()).sort_values(["abs_z","Date","canonical_research_symbol"],ascending=[False,True,True]).head(100)
 examples=sorted(ev.loc[ev.s1_eligible,"canonical_research_symbol"].unique())[:3];pd.DataFrame({"canonical_research_symbol":examples,"selection_rule":"first_three_alphabetical_symbols_with_valid_s1_history"}).to_csv(a.tables_dir/"phase7_mechanical_examples.csv",index=False)
 # Persist all primary results.
 ev.to_parquet(a.processed_dir/"phase7_abnormal_signal_panel.parquet",index=False);summary.to_csv(a.tables_dir/"phase7_s0_s1_summary.csv",index=False);paired_summary.to_csv(a.tables_dir/"phase7_paired_differences.csv",index=False);s0ic.to_csv(a.tables_dir/"phase7_daily_ic_s0_paired.csv",index=False);s1ic.to_csv(a.tables_dir/"phase7_daily_ic_s1.csv",index=False);s0ls.to_csv(a.tables_dir/"phase7_daily_ls_s0_paired.csv",index=False);s1ls.to_csv(a.tables_dir/"phase7_daily_ls_s1.csv",index=False);s0dec.to_csv(a.tables_dir/"phase7_deciles_s0_paired.csv",index=False);s1dec.to_csv(a.tables_dir/"phase7_deciles_s1.csv",index=False);pd.DataFrame(subs).to_csv(a.tables_dir/"phase7_subperiod_ic.csv",index=False);rankcorr.to_csv(a.tables_dir/"phase7_daily_s0_s1_rank_correlation.csv",index=False);eligibility.to_csv(a.tables_dir/"phase7_eligibility_summary.csv",index=False);daily_elig.to_csv(a.tables_dir/"phase7_daily_eligibility.csv",index=False);sec_elig.to_csv(a.tables_dir/"phase7_security_eligibility.csv",index=False);pd.DataFrame(dist).to_csv(a.tables_dir/"phase7_distributions.csv",index=False);extreme.to_csv(a.tables_dir/"phase7_extreme_z.csv",index=False)
 # Figures
 for dec,label,color in [(s0dec,"S0","#888888"),(s1dec,"S1","#2455a6")]:plt.errorbar(dec.decile,dec.mean_return,yerr=1.96*dec.hac5_se,fmt="o-",label=label,color=color,capsize=3)
 plt.xlabel("Decile (10 = highest alpha)");plt.ylabel("Mean next-session O-C return");plt.legend();plt.tight_layout();plt.savefig(a.figures_dir/"phase7_s0_s1_decile_comparison.png",dpi=150);plt.close()
 for ls,label,color in [(s0ls,"S0","#888888"),(s1ls,"S1","#2455a6")]:plt.plot(ls.Date,(1+ls.long_short).cumprod()-1,label=label,color=color)
 plt.ylabel("Cumulative gross D10-D1 return");plt.legend();plt.tight_layout();plt.savefig(a.figures_dir/"phase7_s0_s1_cumulative_comparison.png",dpi=150);plt.close()
 s0ic["roll"]=s0ic.rank_ic.rolling(60).mean();s1ic["roll"]=s1ic.rank_ic.rolling(60).mean();plt.plot(s0ic.Date,s0ic.roll,label="S0",color="#888888");plt.plot(s1ic.Date,s1ic.roll,label="S1",color="#2455a6");plt.axhline(0,color="black",lw=.6);plt.ylabel("60-day mean Rank IC");plt.legend();plt.tight_layout();plt.savefig(a.figures_dir/"phase7_s0_s1_rolling_ic.png",dpi=150);plt.close()
 for sym in examples:
  d=panel.loc[panel.canonical_research_symbol.eq(sym)].sort_values("Date");fig,ax=plt.subplots(figsize=(9,4));ax.plot(d.Date,d.q,label="q");ax.plot(d.Date,d.historical_median,label="median");ax2=ax.twinx();ax2.plot(d.Date,d.historical_mad,label="MAD",color="tab:red",alpha=.7);ax.set_title(f"{sym}: mechanically selected rolling q baseline");ax.legend(loc="upper left");ax2.legend(loc="upper right");fig.tight_layout();fig.savefig(a.figures_dir/f"phase7_example_{sym}_rolling_q_median_mad.png",dpi=150);plt.close(fig)
 print(json.dumps({"paired_rows":len(paired),"days":paired.Date.nunique(),"examples":examples},indent=2))
if __name__=="__main__":main()
