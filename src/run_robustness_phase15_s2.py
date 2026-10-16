"""Phase 15 robustness and falsification analysis for S2, the frozen robustness
comparator, mirroring Phase 11's methodology (originally run on S1) exactly.

Governance note: S2 has NOT been promoted to primary anywhere in this project.
Frozen Phase 9 roles are unchanged (S1 primary, S0 baseline, S2 robustness
comparator). This phase is an additive extension of the Phase 11 robustness
battery to the comparator signal for parity/completeness, not a validation of
a role change. See docs/phase15_robustness_S2_report.md.

Every parameter below is reused unchanged from Phase 11 (src/run_robustness_phase11.py):
rolling window, HAC lags, breadth fractions, cost grid, and the placebo seed
(20260911), reused specifically for direct comparability to Phase 11's own S1
result. Both the additional and original samples are covered, matching Phase
11's own scope.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats


SAMPLES = {
    "additional_2023-01-03_2025-05-27": ("2023-01-03", "2025-05-27"),
    "original_2025-05-28_2026-08-31": ("2025-05-28", "2026-08-31"),
}
COST_BPS = (0.0, 1.0, 2.5, 5.0)
PRIMARY_COST = 2.5
HAC_LAGS = (0, 5, 10, 20)
PLACEBO_SEED = 20260911  # Reused unchanged from Phase 11 for direct comparability.
PLACEBO_N = 1000
GL_DATE = pd.Timestamp("2024-04-10")
GL_SECURITY = "current_cik_0000320335_symbol_GL"


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_artifact_paths(root: Path) -> list[Path]:
    """Identical to Phase 11's source list: S2's raw/bounded fields and S2_continuous
    strategy live in these same frozen Phase 9/10 artifacts alongside S0/S1."""
    explicit = [
        root / "data/processed/phase9_final_rank_score_panel.parquet",
        root / "data/processed/candidate_history_panel.parquet",
        root / "data/processed/phase7a_candidate_history_panel.parquet",
        root / "data/processed/phase10_daily_portfolio_exposure_panel.parquet",
        root / "data/processed/phase10_portfolio_position_panel.parquet",
        root / "data/processed/phase10_daily_portfolio_returns_by_cost.parquet",
        root / "docs/phase7a_report.md",
        root / "docs/phase7b_candidate_history_report.md",
        root / "docs/phase8_report.md",
        root / "docs/phase9_report.md",
        root / "docs/phase10_report.md",
        root / "src/run_realistic_backtest_phase10.py",
        root / "tests/test_phase10_backtest.py",
    ]
    for prefix in ("phase7a_", "phase7b_", "phase8_", "phase9_", "phase10_"):
        explicit.extend(sorted((root / "results/tables").glob(f"{prefix}*")))
        explicit.extend(sorted((root / "results/figures").glob(f"{prefix}*")))
    return sorted(set(path for path in explicit if path.exists()))


def source_manifest(root: Path) -> tuple[Path, int]:
    manifest = root / "preservation/phase15_pre_robustness_s2_source_artifacts/SHA256SUMS.txt"
    paths = source_artifact_paths(root)
    if not manifest.exists():
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text("\n".join(f"{hash_file(p)}  {p.relative_to(root)}" for p in paths) + "\n")
    failures = []
    for line in manifest.read_text().splitlines():
        digest, relative = line.split("  ", 1)
        path = root / relative
        if not path.exists() or hash_file(path) != digest:
            failures.append(relative)
    if failures:
        raise AssertionError(f"Phase 15 source artifact hash mismatch: {failures}")
    return manifest, len(paths)


def hac_stats(values: pd.Series, lags: int) -> dict[str, float]:
    x = values.dropna().astype(float)
    if len(x) < 2:
        return {"mean": np.nan, "se": np.nan, "t": np.nan, "two_sided_p": np.nan, "one_sided_p_greater_zero": np.nan}
    fit = sm.OLS(x.to_numpy(), np.ones((len(x), 1))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    mean, se, t = float(fit.params[0]), float(fit.bse[0]), float(fit.tvalues[0])
    return {"mean": mean, "se": se, "t": t, "two_sided_p": float(2 * stats.norm.sf(abs(t))), "one_sided_p_greater_zero": float(stats.norm.sf(t))}


def portfolio_stats(values: pd.Series, lags: int = 5) -> dict[str, float]:
    x = values.dropna().astype(float)
    stat = hac_stats(x, lags)
    if not len(x):
        return {**stat, "days": 0, "mean_bps": np.nan, "annualized_volatility": np.nan, "sharpe": np.nan, "cumulative_return": np.nan, "maximum_drawdown": np.nan, "positive_day_fraction": np.nan}
    equity = (1 + x).cumprod()
    dd = equity / equity.cummax() - 1
    std = x.std(ddof=1)
    return {**stat, "days": len(x), "mean_bps": stat["mean"] * 10000, "annualized_volatility": std * np.sqrt(252), "sharpe": stat["mean"] / std * np.sqrt(252) if std > 0 else np.nan, "cumulative_return": float(equity.iloc[-1] - 1), "maximum_drawdown": float(dd.min()), "positive_day_fraction": float((x > 0).mean())}


def stable_scores(day: pd.DataFrame, raw_column: str = "S2") -> pd.Series:
    """Rank raw S2 low-to-high with canonical alphabetical tie breaks, target-free."""
    result = pd.Series(np.nan, index=day.index, dtype=float)
    eligible = day.loc[day[raw_column].notna(), [raw_column, "canonical_research_symbol"]].sort_values([raw_column, "canonical_research_symbol"], kind="stable")
    n = len(eligible)
    if n:
        ranks = np.arange(1, n + 1)
        result.loc[eligible.index] = 0.0 if n == 1 else 2 * (ranks - 1) / (n - 1) - 1
    return result


def continuous_weights(scores: pd.Series) -> pd.Series:
    out = pd.Series(np.nan, index=scores.index, dtype=float)
    valid = scores.notna()
    denom = float(scores.loc[valid].abs().sum())
    if valid.any() and denom > 0:
        out.loc[valid] = scores.loc[valid] / denom
    return out


def validate_weights(weights: pd.Series) -> None:
    w = weights.dropna()
    if w.empty:
        return
    assert np.isclose(w.abs().sum(), 1, atol=1e-12, rtol=0)
    assert np.isclose(w.sum(), 0, atol=1e-12, rtol=0)
    assert np.isclose(w.clip(lower=0).sum(), .5, atol=1e-12, rtol=0)
    assert np.isclose(-w.clip(upper=0).sum(), .5, atol=1e-12, rtol=0)


def tail_weights(day: pd.DataFrame, fraction: float) -> pd.Series:
    out = pd.Series(np.nan, index=day.index, dtype=float)
    ranked = day.loc[day["S2"].notna(), ["S2", "canonical_research_symbol"]].sort_values(["S2", "canonical_research_symbol"], kind="stable")
    n = len(ranked); k = max(1, int(np.ceil(fraction * n)))
    if n < 2 or 2 * k > n:
        return out
    out.loc[ranked.index] = 0.0
    out.loc[ranked.index[:k]] = -0.5 / k
    out.loc[ranked.index[-k:]] = 0.5 / k
    return out


def exact_prior_adv(root: Path, panel: pd.DataFrame) -> pd.DataFrame:
    """Use the Phase 10 exactly-prior-20 raw Close×Volume diagnostic, sourced from the
    S2_continuous position rows (a security-level metric, identical regardless of which
    continuous strategy it is merged from, since all continuous strategies share the same
    score-eligible universe each day)."""
    positions = pd.read_parquet(root / "data/processed/phase10_portfolio_position_panel.parquet")
    adv = positions.loc[positions["strategy"].eq("S2_continuous"), ["sample", "Date", "canonical_research_symbol", "prior_median_dollar_volume_20"]].drop_duplicates()
    return panel.merge(adv, on=["sample", "Date", "canonical_research_symbol"], how="left", validate="one_to_one")


def liquidity_neutral_scores(day: pd.DataFrame) -> pd.Series:
    """Demean frozen bounded S2 score within daily prior-ADV quintiles."""
    result = pd.Series(np.nan, index=day.index, dtype=float)
    work = day.loc[day["S2_bounded_rank_score"].notna() & day["prior_median_dollar_volume_20"].gt(0), ["S2_bounded_rank_score", "prior_median_dollar_volume_20", "canonical_research_symbol"]].copy()
    if not len(work):
        return result
    ordered = work.sort_values(["prior_median_dollar_volume_20", "canonical_research_symbol"], kind="stable")
    ordered["quintile"] = np.floor(np.arange(len(ordered)) * 5 / len(ordered)).astype(int) + 1
    demeaned = ordered["S2_bounded_rank_score"] - ordered.groupby("quintile")["S2_bounded_rank_score"].transform("mean")
    result.loc[demeaned.index] = demeaned
    return result


def evaluate_weights(panel: pd.DataFrame, name: str, score_func, cost_cases: tuple[float, ...] = COST_BPS) -> tuple[pd.DataFrame, pd.DataFrame]:
    daily, positions = [], []
    for (sample, date), day in panel.groupby(["sample", "Date"], sort=True):
        day = day.copy(); scores = score_func(day); weights = continuous_weights(scores) if name.endswith("continuous") or name.endswith("neutral") or name.startswith("S2_fixed") else scores
        day["_robustness_score"] = scores; day["weight"] = weights
        validate_weights(weights.dropna())
        invested = weights.notna() & weights.abs().gt(0)
        missing = invested & (day["forward_oc_return"].isna() | ~day["target_available"].fillna(False))
        target_dates = day.loc[invested, "designated_target_date"].dropna().unique()
        if len(target_dates) > 1:
            raise AssertionError(f"{sample} {date}: multiple target dates")
        available = bool(invested.any() and not missing.any())
        gross = float((weights.loc[invested] * day.loc[invested, "forward_oc_return"]).sum()) if available else np.nan
        daily.append({"sample": sample, "signal_date": date, "strategy": name, "trade_date": target_dates[0] if len(target_dates) else pd.NaT, "available": available, "missing_target_symbols": ";".join(day.loc[missing, "canonical_research_symbol"].astype(str).sort_values()), "position_count": int(invested.sum()), "gross_exposure": float(weights.dropna().abs().sum()) if weights.notna().any() else np.nan, "net_exposure": float(weights.dropna().sum()) if weights.notna().any() else np.nan, "gross_return": gross, "max_abs_weight": float(weights.loc[invested].abs().max()) if invested.any() else np.nan, "top10_abs_weight_concentration": float(weights.loc[invested].abs().nlargest(10).sum()) if invested.any() else np.nan})
        positions.append(day.loc[weights.notna(), ["sample", "Date", "canonical_research_symbol", "S2", "S2_bounded_rank_score", "forward_oc_return", "target_available", "weight", "prior_median_dollar_volume_20"]].assign(strategy=name, nonzero_position=invested.loc[weights.notna()].to_numpy()))
    daily_df, position_df = pd.DataFrame(daily), pd.concat(positions, ignore_index=True)
    rows = []
    for row in daily_df.itertuples(index=False):
        for cost in cost_cases:
            net = row.gross_return - 2 * cost / 10000 if row.available else np.nan
            rows.append({"sample": row.sample, "signal_date": row.signal_date, "trade_date": row.trade_date, "strategy": row.strategy, "available": row.available, "one_way_cost_bps": cost, "gross_return": row.gross_return, "net_return": net})
    return daily_df, position_df


def daily_ic(panel: pd.DataFrame, score_column: str = "S2") -> pd.DataFrame:
    rows = []
    for (sample, date), day in panel.groupby(["sample", "Date"]):
        valid = day.loc[day[score_column].notna() & day["target_available"].fillna(False) & day["forward_oc_return"].notna()]
        value = stats.spearmanr(valid[score_column], valid["forward_oc_return"]).statistic if len(valid) >= 3 and valid[score_column].nunique() > 1 else np.nan
        rows.append({"sample": sample, "signal_date": date, "rank_ic": value, "observations": len(valid)})
    return pd.DataFrame(rows)


def performance_rows(returns: pd.DataFrame, label: str, lags: tuple[int, ...] = (5,)) -> pd.DataFrame:
    rows = []
    for (sample, strategy, cost), group in returns.groupby(["sample", "strategy", "one_way_cost_bps"], sort=True):
        x = group.loc[group["available"], "net_return"]
        for lag in lags:
            stat = portfolio_stats(x, lag)
            rows.append({"sample": sample, "strategy": strategy, "test": label, "one_way_cost_bps": cost, "hac_lag": lag, **stat})
    return pd.DataFrame(rows)


def time_tables(returns: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows, hrows, rolling = [], [], []
    primary = returns.loc[returns.strategy.eq("S2_continuous")]
    for (sample, cost), group in primary.groupby(["sample", "one_way_cost_bps"]):
        group = group.sort_values("signal_date").copy(); group["year"] = pd.to_datetime(group.signal_date).dt.year
        for year, values in group.loc[group.available].groupby("year"):
            for kind, col in [("gross", "gross_return"), ("net", "net_return")]:
                rows.append({"sample": sample, "period": f"calendar_year_{year}", "return_type": kind, "one_way_cost_bps": cost, **portfolio_stats(values[col], 5)})
        n = group.signal_date.nunique(); half = n // 2; dates = sorted(group.signal_date.unique())
        for name, dateset in [("first_half", set(dates[:half])), ("second_half", set(dates[half:]))]:
            values = group.loc[group.signal_date.isin(dateset) & group.available]
            for kind, col in [("gross", "gross_return"), ("net", "net_return")]:
                rows.append({"sample": sample, "period": name, "return_type": kind, "one_way_cost_bps": cost, **portfolio_stats(values[col], 5)})
        sub = [("predefined_subperiod_1", "2025-05-28", "2026-01-13"), ("predefined_subperiod_2", "2026-01-14", "2026-08-31")] if sample.startswith("original") else [("additional_full_period", *SAMPLES[sample])]
        for name, start, end in sub:
            values = group.loc[group.signal_date.between(start, end) & group.available]
            for kind, col in [("gross", "gross_return"), ("net", "net_return")]:
                rows.append({"sample": sample, "period": name, "return_type": kind, "one_way_cost_bps": cost, **portfolio_stats(values[col], 5)})
        values = group.loc[group.available]
        for lag in HAC_LAGS:
            for kind, col in [("gross", "gross_return"), ("net", "net_return")]:
                rows.append({"sample": sample, "period": "full_sample", "return_type": kind, "one_way_cost_bps": cost, **portfolio_stats(values[col], lag), "hac_lag": lag})
        hrows.extend([r for r in rows if r["sample"] == sample and r["period"] == "full_sample" and r.get("hac_lag") is not None and r["one_way_cost_bps"] == cost])
        group["rolling_mean_gross"] = group.gross_return.where(group.available).rolling(63).mean(); group["rolling_sharpe_gross"] = group.gross_return.where(group.available).rolling(63).mean() / group.gross_return.where(group.available).rolling(63).std(ddof=1) * np.sqrt(252)
        group["rolling_mean_net"] = group.net_return.where(group.available).rolling(63).mean(); group["rolling_sharpe_net"] = group.net_return.where(group.available).rolling(63).mean() / group.net_return.where(group.available).rolling(63).std(ddof=1) * np.sqrt(252)
        rolling.append(group[["sample", "signal_date", "one_way_cost_bps", "rolling_mean_gross", "rolling_sharpe_gross", "rolling_mean_net", "rolling_sharpe_net"]])
    return pd.DataFrame(rows), pd.DataFrame(hrows).drop_duplicates(), pd.concat(rolling, ignore_index=True)


def fixed_universe_panel(panel: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for sample, group in panel.groupby("sample"):
        first = group.loc[group.Date.eq(group.Date.min()) & group.universe_member, "canonical_research_symbol"]
        parts.append(group.loc[group.canonical_research_symbol.isin(set(first))].copy())
    return pd.concat(parts, ignore_index=True)


def flagged_observations(root: Path, panel: pd.DataFrame) -> set[tuple[pd.Timestamp, str]]:
    paths = [root / "results/tables/phase4_extreme_forward_oc_returns.csv", root / "results/tables/phase7a_extreme_forward_returns.csv"]
    flags = set()
    id_cols = [c for c in ["canonical_research_symbol", "source_symbol", "yahoo_symbol", "finra_symbol", "finra_symbol_x", "finra_symbol_y"] if c in panel.columns]
    for path in paths:
        if not path.exists():
            continue
        table = pd.read_csv(path)
        for row in table.itertuples(index=False):
            date = pd.Timestamp(row.Date)
            symbol = str(getattr(row, "canonical_research_symbol", ""))
            matches = panel.loc[panel.Date.eq(date) & panel[id_cols].astype(str).eq(symbol).any(axis=1), "canonical_research_symbol"]
            for canonical in matches:
                flags.add((date, canonical))
    return flags


def exclusion_sensitivity(daily: pd.DataFrame, positions: pd.DataFrame, flags: set[tuple[pd.Timestamp, str]]) -> pd.DataFrame:
    impacted = positions.loc[(positions.strategy.eq("S2_continuous")) & positions.nonzero_position & positions.apply(lambda r: (pd.Timestamp(r.Date), r.canonical_research_symbol) in flags, axis=1), ["sample", "Date"]].drop_duplicates()
    rows = []
    for sample, group in daily.loc[daily.strategy.eq("S2_continuous")].groupby("sample"):
        for cost in (0.0, PRIMARY_COST):
            base = group.loc[group.available].copy(); base["net"] = base.gross_return - 2 * cost / 10000
            drop = impacted.loc[impacted["sample"].eq(sample), "Date"]
            kept = base.loc[~base.signal_date.isin(drop)]
            rows.append({"sample": sample, "exclusion_set": "all_previously_flagged_extreme_targets", "one_way_cost_bps": cost, "impacted_strategy_days": len(drop), "base_mean_bps": portfolio_stats(base.net)["mean_bps"], "excluded_mean_bps": portfolio_stats(kept.net)["mean_bps"], "base_cumulative": portfolio_stats(base.net)["cumulative_return"], "excluded_cumulative": portfolio_stats(kept.net)["cumulative_return"]})
            gl_drop = group.loc[group.signal_date.eq(GL_DATE) & group.available, "signal_date"]
            gl_kept = base.loc[~base.signal_date.isin(gl_drop)]
            rows.append({"sample": sample, "exclusion_set": "globe_life_only", "one_way_cost_bps": cost, "impacted_strategy_days": len(gl_drop), "base_mean_bps": portfolio_stats(base.net)["mean_bps"], "excluded_mean_bps": portfolio_stats(gl_kept.net)["mean_bps"], "base_cumulative": portfolio_stats(base.net)["cumulative_return"], "excluded_cumulative": portfolio_stats(gl_kept.net)["cumulative_return"]})
    gl_flags = {(GL_DATE, GL_SECURITY)}
    return pd.DataFrame(rows), impacted, gl_flags


def influence_tables(daily: pd.DataFrame, positions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = daily.loc[daily.strategy.eq("S2_continuous") & daily.available].copy()
    day_rows = []
    for sample, group in base.groupby("sample"):
        for kind, order in [("best", False), ("worst", True)]:
            ordered = group.sort_values("gross_return", ascending=order)
            for k in (1, 5, 10):
                selected = ordered.head(k)
                day_rows.append({"sample": sample, "selection": kind, "k_days": k, "mean_selected_bps": selected.gross_return.mean() * 10000, "sum_selected_bps": selected.gross_return.sum() * 10000, "selected_geometric_return": float((1 + selected.gross_return).prod() - 1), "dates": ";".join(pd.to_datetime(selected.signal_date).dt.strftime("%Y-%m-%d"))})
    pos = positions.loc[positions.strategy.eq("S2_continuous") & positions.nonzero_position & positions.forward_oc_return.notna()].copy(); pos["contribution"] = pos.weight * pos.forward_oc_return
    sec = pos.groupby(["sample", "canonical_research_symbol"], as_index=False).agg(contribution_sum=("contribution", "sum"), days=("contribution", "size")); sec["abs_contribution_sum"] = sec.contribution_sum.abs(); sec = sec.sort_values(["sample", "abs_contribution_sum"], ascending=[True, False]); sec["rank"] = sec.groupby("sample").cumcount() + 1
    loo = []
    for sample, group in base.groupby("sample"):
        group["year"] = pd.to_datetime(group.signal_date).dt.year
        for year in sorted(group.year.unique()):
            kept = group.loc[group.year.ne(year)]
            loo.append({"sample": sample, "excluded_year": int(year), "mean_gross_bps": kept.gross_return.mean() * 10000, "mean_sign_positive": bool(kept.gross_return.mean() > 0), "cumulative_gross": float((1 + kept.gross_return).prod() - 1)})
    return pd.DataFrame(day_rows), sec, pd.DataFrame(loo)


def placebo(panel: pd.DataFrame, actual_means: dict[str, float]) -> pd.DataFrame:
    rng = np.random.default_rng(PLACEBO_SEED); rows = []
    for sample, group in panel.groupby("sample"):
        daily_arrays = []
        for date, day in group.groupby("Date"):
            valid = day.loc[day.S2.notna()].copy()
            if len(valid) > 1:
                daily_arrays.append((date, valid.S2.to_numpy(float), valid.forward_oc_return.to_numpy(float), valid.target_available.fillna(False).to_numpy()))
        means = np.full(PLACEBO_N, np.nan)
        for i in range(PLACEBO_N):
            values = []
            for _, scores, returns, available in daily_arrays:
                shuffled = rng.permutation(scores); denom = np.abs(shuffled).sum()
                if denom <= 0:
                    continue
                weights = shuffled / denom
                if np.any((np.abs(weights) > 0) & (~available | ~np.isfinite(returns))):
                    continue
                values.append(float(np.dot(weights, returns)))
            means[i] = np.mean(values) if values else np.nan
        actual = actual_means[sample]
        empirical = (np.sum(means >= actual) + 1) / (np.sum(np.isfinite(means)) + 1)
        for i, value in enumerate(means, 1):
            rows.append({"sample": sample, "permutation": i, "placebo_mean_return": value, "actual_mean_return": actual, "empirical_one_sided_p": empirical, "seed": PLACEBO_SEED, "permutations": PLACEBO_N})
    return pd.DataFrame(rows)


def make_figures(root: Path, placebo_table: pd.DataFrame, rolling: pd.DataFrame, breadth: pd.DataFrame) -> None:
    figures = root / "results/figures"; figures.mkdir(parents=True, exist_ok=True)
    for sample, group in placebo_table.groupby("sample"):
        plt.figure(figsize=(7, 4)); plt.hist(group.placebo_mean_return.dropna() * 10000, bins=35, color="#8c8c8c", alpha=.85); plt.axvline(group.actual_mean_return.iloc[0] * 10000, color="#c44e52", lw=2, label="Actual S2"); plt.xlabel("Mean gross daily return (bps)"); plt.ylabel("Permutation count"); plt.legend(); plt.tight_layout(); short = "additional" if sample.startswith("additional") else "original"; plt.savefig(figures / f"phase15_{short}_placebo_distribution.png", dpi=150); plt.close()
    for sample, group in rolling.loc[rolling.one_way_cost_bps.eq(PRIMARY_COST)].groupby("sample"):
        short = "additional" if sample.startswith("additional") else "original"; plt.figure(figsize=(8, 3.5)); plt.plot(group.signal_date, group.rolling_sharpe_gross, label="Gross", color="#2468a2"); plt.plot(group.signal_date, group.rolling_sharpe_net, label="Net 2.5 bps/side", color="#c44e52"); plt.axhline(0, color="black", lw=.6); plt.legend(); plt.ylabel("63-session rolling Sharpe"); plt.tight_layout(); plt.savefig(figures / f"phase15_{short}_rolling_stability.png", dpi=150); plt.close()
    plt.figure(figsize=(8, 4)); view = breadth.loc[breadth.one_way_cost_bps.isin([0, 1, 2.5])].copy(); labels = list(view.strategy.unique()); x = np.arange(len(labels)); width = .24
    for j, cost in enumerate([0.0, 1.0, 2.5]):
        values = [view.loc[(view.strategy.eq(label)) & view.one_way_cost_bps.eq(cost), "mean_bps"].iloc[0] for label in labels]
        plt.bar(x + (j - 1) * width, values, width, label=f"{cost:g} bps/side")
    plt.xticks(x, [label.replace("S2_", "") for label in labels], rotation=20); plt.ylabel("Mean daily return (bps)"); plt.xlabel("Breadth variant"); plt.legend(); plt.tight_layout(); plt.savefig(figures / "phase15_breadth_comparison.png", dpi=150); plt.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--root", type=Path, default=Path(".")); args = parser.parse_args(); root = args.root.resolve()
    manifest, source_count = source_manifest(root)
    panel = pd.read_parquet(root / "data/processed/phase9_final_rank_score_panel.parquet"); panel["Date"] = pd.to_datetime(panel.Date); panel["designated_target_date"] = pd.to_datetime(panel.designated_target_date)
    if panel.duplicated(["sample", "Date", "canonical_research_symbol"]).any(): raise AssertionError("duplicate panel key")
    panel = exact_prior_adv(root, panel)
    # Reproduce Phase 10's S2 daily portfolio before any variant is evaluated.
    primary_daily = pd.read_parquet(root / "data/processed/phase10_daily_portfolio_exposure_panel.parquet"); primary_daily["signal_date"] = pd.to_datetime(primary_daily.signal_date)
    primary_expected = primary_daily.loc[primary_daily.strategy.eq("S2_continuous"), ["sample", "signal_date", "strategy_day_available", "gross_return", "gross_exposure", "net_exposure"]].sort_values(["sample", "signal_date"]).reset_index(drop=True)
    rebuilt_daily, rebuilt_positions = evaluate_weights(panel, "S2_continuous", lambda day: day.S2_bounded_rank_score)
    rebuilt_check = rebuilt_daily.rename(columns={"available": "strategy_day_available", "signal_date": "signal_date"})[["sample", "signal_date", "strategy_day_available", "gross_return", "gross_exposure", "net_exposure"]].sort_values(["sample", "signal_date"]).reset_index(drop=True)
    if len(primary_expected) != len(rebuilt_check) or not np.array_equal(primary_expected.strategy_day_available.to_numpy(), rebuilt_check.strategy_day_available.to_numpy()) or not np.allclose(primary_expected.gross_return.fillna(0), rebuilt_check.gross_return.fillna(0), atol=1e-15, rtol=0) or not np.allclose(primary_expected.gross_exposure.fillna(0), rebuilt_check.gross_exposure.fillna(0), atol=1e-15, rtol=0):
        raise AssertionError("Phase 10 S2 daily returns were not reproduced exactly")
    score_panel = panel
    all_daily, all_positions, all_returns = [rebuilt_daily], [rebuilt_positions], []
    for fraction in (.05, .10, .20):
        d, p = evaluate_weights(score_panel, f"S2_top_bottom_{int(fraction*100)}pct", lambda day, f=fraction: tail_weights(day, f)); all_daily.append(d); all_positions.append(p)
    fixed = fixed_universe_panel(score_panel); d, p = evaluate_weights(fixed, "S2_fixed_universe_continuous", lambda day: stable_scores(day, "S2")); all_daily.append(d); all_positions.append(p)
    d, p = evaluate_weights(score_panel, "S2_liquidity_neutral_continuous", liquidity_neutral_scores); all_daily.append(d); all_positions.append(p)
    daily = pd.concat(all_daily, ignore_index=True); positions = pd.concat(all_positions, ignore_index=True)
    returns_rows = []
    for row in daily.itertuples(index=False):
        for cost in COST_BPS:
            returns_rows.append({"sample": row.sample, "signal_date": row.signal_date, "trade_date": row.trade_date, "strategy": row.strategy, "available": row.available, "one_way_cost_bps": cost, "gross_return": row.gross_return, "net_return": row.gross_return - 2*cost/10000 if row.available else np.nan})
    returns = pd.DataFrame(returns_rows)
    ic_rows = []
    for strategy, source in [("S2_primary", score_panel), ("S2_fixed_universe", fixed)]:
        metric = "S2_bounded_rank_score" if strategy == "S2_primary" else "S2"
        ic = daily_ic(source, metric).rename(columns={"rank_ic": "rank_ic"}); ic["strategy"] = strategy; ic_rows.append(ic)
    ic_table = pd.concat(ic_rows, ignore_index=True)
    perf = performance_rows(returns, "phase15_variant", (5,)); time_table, hac_table, rolling = time_tables(returns)
    breadth = perf.loc[perf.strategy.isin(["S2_continuous", "S2_top_bottom_5pct", "S2_top_bottom_10pct", "S2_top_bottom_20pct"])].copy()
    fixed_perf = perf.loc[perf.strategy.eq("S2_fixed_universe_continuous")].copy()
    neutral_perf = perf.loc[perf.strategy.eq("S2_liquidity_neutral_continuous")].copy()
    sector_table = pd.DataFrame([{"sample": sample, "sector_field_found": False, "classification_coverage": 0.0, "status": "unavailable_existing_panel_has_no_sector_classification", "result": "not_calculated"} for sample in SAMPLES])
    adv_quintile = []
    for sample, group in positions.loc[positions.strategy.eq("S2_liquidity_neutral_continuous")].groupby("sample"):
        adv_quintile.append({"sample": sample, "positions": len(group), "valid_prior_adv": int(group.prior_median_dollar_volume_20.gt(0).sum()), "missing_prior_adv": int(group.prior_median_dollar_volume_20.le(0).sum()), "neutral_strategy_days": int(daily.loc[(daily["sample"].eq(sample)) & daily.strategy.eq("S2_liquidity_neutral_continuous") & daily.available].shape[0])})
    controls = pd.concat([neutral_perf.assign(control="liquidity_neutral"), sector_table.assign(control="sector_neutral")], ignore_index=True, sort=False)
    flags = flagged_observations(root, panel); sensitivity, impacted, gl_flags = exclusion_sensitivity(rebuilt_daily, rebuilt_positions, flags)
    day_influence, security_influence, loo = influence_tables(rebuilt_daily, rebuilt_positions)
    actual_means = {sample: portfolio_stats(rebuilt_daily.loc[rebuilt_daily["sample"].eq(sample) & rebuilt_daily.available, "gross_return"])["mean"] for sample in SAMPLES}
    placebo_table = placebo(panel, actual_means)
    placebo_summary = placebo_table.groupby("sample").agg(actual_mean_return=("actual_mean_return", "first"), placebo_mean=("placebo_mean_return", "mean"), placebo_std=("placebo_mean_return", "std"), empirical_one_sided_p=("empirical_one_sided_p", "first"), permutations=("permutations", "first"), seed=("seed", "first")).reset_index()
    out = root / "results/tables"; proc = root / "data/processed"; out.mkdir(parents=True, exist_ok=True); proc.mkdir(parents=True, exist_ok=True)
    top10_security = security_influence.groupby("sample", group_keys=False).head(10)
    time_table.to_csv(out / "phase15_time_stability.csv", index=False); hac_table.to_csv(out / "phase15_hac_lag_sensitivity.csv", index=False); rolling.to_csv(out / "phase15_rolling_63_session.csv", index=False); breadth.to_csv(out / "phase15_breadth_comparison.csv", index=False); fixed_perf.to_csv(out / "phase15_fixed_universe_results.csv", index=False); controls.to_csv(out / "phase15_sector_liquidity_neutral.csv", index=False); pd.DataFrame(adv_quintile).to_csv(out / "phase15_liquidity_coverage.csv", index=False); sensitivity.to_csv(out / "phase15_outlier_sensitivity.csv", index=False); day_influence.to_csv(out / "phase15_day_influence.csv", index=False); top10_security.to_csv(out / "phase15_security_influence_top10.csv", index=False); loo.to_csv(out / "phase15_leave_one_year_out.csv", index=False); placebo_table.to_csv(out / "phase15_placebo_permutations.csv", index=False); placebo_summary.to_csv(out / "phase15_placebo_summary.csv", index=False); ic_table.to_csv(out / "phase15_rank_ic_diagnostics.csv", index=False)
    daily.to_parquet(proc / "phase15_daily_robustness_s2_portfolio_panel.parquet", index=False); positions.to_parquet(proc / "phase15_robustness_s2_positions.parquet", index=False)
    make_figures(root, placebo_table, rolling, breadth)
    robustness_summary = pd.concat([
        perf.loc[perf.strategy.isin(["S2_continuous", "S2_top_bottom_5pct", "S2_top_bottom_10pct", "S2_top_bottom_20pct", "S2_fixed_universe_continuous", "S2_liquidity_neutral_continuous"])].assign(result_family="portfolio_variant"),
        placebo_summary.assign(result_family="placebo"),
        sensitivity.assign(result_family="outlier_sensitivity"),
    ], ignore_index=True, sort=False)
    robustness_summary.to_csv(out / "phase15_robustness_summary.csv", index=False)
    _, verified = source_manifest(root)
    print(json.dumps({"source_artifacts_verified": verified, "phase10_S2_reproduced": True, "daily_variant_rows": len(daily), "placebo_permutations": PLACEBO_N, "placebo_seed": PLACEBO_SEED, "flags": len(flags)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
