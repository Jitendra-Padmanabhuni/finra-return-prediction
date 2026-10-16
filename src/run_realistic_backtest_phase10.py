"""Phase 10 frozen-score, next-session open-to-close illustrative backtest."""

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


HAC_LAGS = 5
COSTS_BPS = (0.0, 1.0, 2.5, 5.0)
PRIMARY_COST_BPS = 2.5
SAMPLES = {
    "additional_2023-01-03_2025-05-27": ("2023-01-03", "2025-05-27"),
    "original_2025-05-28_2026-08-31": ("2025-05-28", "2026-08-31"),
}
SCORE_COLUMNS = {"S0": "S0_bounded_rank_score", "S1": "final_rank_score", "S2": "S2_bounded_rank_score"}
GL_DATE = pd.Timestamp("2024-04-10")
GL_SECURITY = "current_cik_0000320335_symbol_GL"


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_artifact_paths(root: Path) -> list[Path]:
    explicit = [
        root / "data/processed/phase9_final_rank_score_panel.parquet",
        root / "data/processed/phase7a_candidate_history_panel.parquet",
        root / "data/processed/candidate_history_panel.parquet",
        root / "docs/phase7a_report.md",
        root / "docs/phase7b_candidate_history_report.md",
        root / "docs/phase8_report.md",
        root / "docs/phase9_report.md",
    ]
    tables = []
    for prefix in ("phase7a_", "phase7b_", "phase8_", "phase9_"):
        tables.extend(sorted((root / "results/tables").glob(f"{prefix}*")))
    return sorted(set(explicit + tables))


def create_or_validate_source_manifest(root: Path) -> tuple[Path, int]:
    """Hash the immutable source artifacts that this phase consumes."""
    manifest = root / "preservation/phase10_pre_backtest_source_artifacts/SHA256SUMS.txt"
    paths = source_artifact_paths(root)
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing Phase 10 source artifacts: {missing}")
    if not manifest.exists():
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text("\n".join(f"{hash_file(path)}  {path.relative_to(root)}" for path in paths) + "\n")
    failures = []
    for line in manifest.read_text().splitlines():
        digest, relative = line.split("  ", 1)
        path = root / relative
        if not path.exists() or hash_file(path) != digest:
            failures.append(relative)
    if failures:
        raise AssertionError(f"Phase 10 source artifact hash mismatch: {failures}")
    return manifest, len(paths)


def hac_stats(values: pd.Series) -> dict[str, float]:
    values = values.dropna().astype(float)
    if len(values) < 2:
        return {"mean": np.nan, "hac5_se": np.nan, "hac5_t": np.nan, "two_sided_hac5_p": np.nan, "one_sided_hac5_p_greater_zero": np.nan}
    fit = sm.OLS(values.to_numpy(), np.ones((len(values), 1))).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})
    mean, se, t = float(fit.params[0]), float(fit.bse[0]), float(fit.tvalues[0])
    return {"mean": mean, "hac5_se": se, "hac5_t": t, "two_sided_hac5_p": float(2 * stats.norm.sf(abs(t))), "one_sided_hac5_p_greater_zero": float(stats.norm.sf(t))}


def performance_stats(returns: pd.Series) -> dict[str, float]:
    returns = returns.dropna().astype(float)
    output = hac_stats(returns)
    n = len(returns)
    if not n:
        return {**output, **{key: np.nan for key in ["days", "mean_daily_return_bps", "annualized_volatility", "annualized_sharpe_zero_rf", "cumulative_return", "annualized_compounded_return", "maximum_drawdown", "positive_return_day_fraction", "best_daily_return", "worst_daily_return", "break_even_one_way_cost_bps"]}}
    std = float(returns.std(ddof=1)) if n > 1 else np.nan
    cumulative = (1 + returns).cumprod()
    drawdown = cumulative / cumulative.cummax() - 1
    break_even = output["mean"] * 10_000 / 2  # entry + exit consume twice the one-way cost.
    return {
        **output,
        "days": n,
        "mean_daily_return_bps": output["mean"] * 10_000,
        "annualized_volatility": std * np.sqrt(252),
        "annualized_sharpe_zero_rf": output["mean"] / std * np.sqrt(252) if std and np.isfinite(std) and std > 0 else np.nan,
        "cumulative_return": float(cumulative.iloc[-1] - 1),
        "annualized_compounded_return": float(cumulative.iloc[-1] ** (252 / n) - 1) if cumulative.iloc[-1] > 0 else np.nan,
        "maximum_drawdown": float(drawdown.min()),
        "positive_return_day_fraction": float((returns > 0).mean()),
        "best_daily_return": float(returns.max()),
        "worst_daily_return": float(returns.min()),
        "break_even_one_way_cost_bps": break_even,
    }


def continuous_weights(day: pd.DataFrame, score_column: str) -> pd.Series:
    """Target-independent dollar-neutral weights for a single score cross-section."""
    scores = day[score_column].copy()
    weights = pd.Series(np.nan, index=day.index, dtype=float)
    eligible = scores.notna()
    denom = float(scores.loc[eligible].abs().sum())
    if not eligible.any() or not np.isfinite(denom) or denom <= 0:
        return weights
    weights.loc[eligible] = scores.loc[eligible] / denom
    return weights


def s1_decile_weights(day: pd.DataFrame) -> pd.Series:
    """Target-independent locked stable-first S1 D10-minus-D1 weights."""
    weights = pd.Series(np.nan, index=day.index, dtype=float)
    eligible = day.loc[day["S1"].notna(), ["S1", "canonical_research_symbol"]].sort_values(["S1", "canonical_research_symbol"], kind="stable")
    n = len(eligible)
    if n < 2:
        return weights
    decile = np.floor(np.arange(n) * 10 / n).astype(int) + 1
    bottom, top = eligible.index[decile == 1], eligible.index[decile == 10]
    if not len(bottom) or not len(top):
        return weights
    weights.loc[bottom] = -0.5 / len(bottom)
    weights.loc[top] = 0.5 / len(top)
    # Scores outside the selected tails have zero rather than missing weights: they receive no position.
    weights.loc[eligible.index.difference(bottom.union(top))] = 0.0
    return weights


def validate_weight_vector(weights: pd.Series, strategy: str) -> None:
    nonmissing = weights.dropna()
    if nonmissing.empty:
        return
    if not np.isclose(nonmissing.abs().sum(), 1.0, atol=1e-12, rtol=0):
        raise AssertionError(f"{strategy}: gross exposure is not one")
    if not np.isclose(nonmissing.sum(), 0.0, atol=1e-12, rtol=0):
        raise AssertionError(f"{strategy}: net exposure is not zero")
    if not np.isclose(nonmissing.clip(lower=0).sum(), .5, atol=1e-12, rtol=0):
        raise AssertionError(f"{strategy}: long gross exposure is not 0.5")
    if not np.isclose(-nonmissing.clip(upper=0).sum(), .5, atol=1e-12, rtol=0):
        raise AssertionError(f"{strategy}: short gross exposure is not 0.5")


def add_prior_adv(root: Path, score_panel: pd.DataFrame) -> pd.DataFrame:
    """Attach exact 20-shared-date strictly-prior raw Close×Volume median dollar volume."""
    sources = {
        "additional_2023-01-03_2025-05-27": root / "data/processed/phase7a_candidate_history_panel.parquet",
        "original_2025-05-28_2026-08-31": root / "data/processed/candidate_history_panel.parquet",
    }
    all_adv = []
    for sample, path in sources.items():
        raw = pd.read_parquet(path, columns=["Date", "canonical_research_symbol", "Close", "Volume"])
        raw["Date"] = pd.to_datetime(raw["Date"])
        raw = raw.sort_values(["canonical_research_symbol", "Date"], kind="stable").copy()
        dollar = raw["Close"].where(raw["Close"].gt(0)) * raw["Volume"].where(raw["Volume"].gt(0))
        # min_periods=20 means every exact immediately preceding shared date must be valid.
        raw["prior_median_dollar_volume_20"] = dollar.groupby(raw["canonical_research_symbol"], sort=False).transform(lambda values: values.shift(1).rolling(20, min_periods=20).median())
        raw["sample"] = sample
        start, end = SAMPLES[sample]
        all_adv.append(raw.loc[raw["Date"].between(start, end), ["sample", "Date", "canonical_research_symbol", "prior_median_dollar_volume_20"]])
    adv = pd.concat(all_adv, ignore_index=True)
    if adv.duplicated(["sample", "Date", "canonical_research_symbol"]).any():
        raise AssertionError("Duplicate prior-ADV key")
    output = score_panel.merge(adv, on=["sample", "Date", "canonical_research_symbol"], how="left", validate="one_to_one")
    return output


def form_strategy_days(panel: pd.DataFrame, strategy: str, score_column: str | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Form all weights before looking at targets; emit unavailable days rather than reweight."""
    daily_rows, position_rows = [], []
    for (sample, date), day in panel.groupby(["sample", "Date"], sort=True):
        day = day.copy()
        weights = s1_decile_weights(day) if strategy == "S1_top_bottom_decile" else continuous_weights(day, str(score_column))
        day["weight"] = weights
        invested = day["weight"].notna() & day["weight"].abs().gt(0)
        formed = day["weight"].notna().any()
        if formed:
            validate_weight_vector(day.loc[day["weight"].notna(), "weight"], strategy)
            if strategy != "S1_top_bottom_decile":
                scores = day.loc[day[str(score_column)].notna(), str(score_column)]
                expected = scores / scores.abs().sum()
                if not np.allclose(day.loc[expected.index, "weight"], expected, atol=1e-15, rtol=0):
                    raise AssertionError(f"{strategy}: an individual weight violates the frozen score formula")
        missing_target = invested & (day["forward_oc_return"].isna() | ~day["target_available"].fillna(False))
        unavailable_symbols = ";".join(day.loc[missing_target, "canonical_research_symbol"].astype(str).sort_values())
        available = bool(formed and not missing_target.any())
        target_dates = day.loc[invested, "designated_target_date"].dropna().unique()
        if len(target_dates) > 1:
            raise AssertionError(f"{sample} {date}: multiple trade dates in one strategy day")
        trade_date = target_dates[0] if len(target_dates) == 1 else pd.NaT
        row = {
            "sample": sample, "strategy": strategy, "signal_date": date, "trade_date": trade_date,
            "strategy_day_formed": formed, "strategy_day_available": available,
            "unavailable_reason": "" if available else ("no_eligible_score" if not formed else "nonzero_weight_missing_designated_target"),
            "missing_target_nonzero_positions": int(missing_target.sum()), "missing_target_symbols": unavailable_symbols,
            "eligible_score_count": int(day["weight"].notna().sum()), "position_count": int(invested.sum()),
            "gross_exposure": float(day.loc[day["weight"].notna(), "weight"].abs().sum()) if formed else np.nan,
            "net_exposure": float(day.loc[day["weight"].notna(), "weight"].sum()) if formed else np.nan,
            "long_gross_exposure": float(day.loc[day["weight"].notna(), "weight"].clip(lower=0).sum()) if formed else np.nan,
            "short_gross_exposure": float(-day.loc[day["weight"].notna(), "weight"].clip(upper=0).sum()) if formed else np.nan,
            "max_abs_weight": float(day.loc[invested, "weight"].abs().max()) if invested.any() else np.nan,
            "top10_abs_weight_concentration": float(day.loc[invested, "weight"].abs().nlargest(10).sum()) if invested.any() else np.nan,
        }
        if available:
            contribution = day.loc[invested, "weight"] * day.loc[invested, "forward_oc_return"]
            row.update({
                "gross_return": float(contribution.sum()),
                "long_leg_return": float(contribution.loc[day.loc[invested, "weight"].gt(0)].sum()),
                "short_leg_return": float(contribution.loc[day.loc[invested, "weight"].lt(0)].sum()),
            })
        else:
            row.update({"gross_return": np.nan, "long_leg_return": np.nan, "short_leg_return": np.nan})
        daily_rows.append(row)
        position_rows.append(day.loc[day["weight"].notna(), ["sample", "Date", "canonical_research_symbol", "S0", "S1", "S2", "final_rank_score", "S0_bounded_rank_score", "S2_bounded_rank_score", "weight", "forward_oc_return", "target_available", "designated_target_date", "prior_median_dollar_volume_20"]].assign(strategy=strategy, nonzero_position=invested.loc[day["weight"].notna()].to_numpy()))
    daily = pd.DataFrame(daily_rows)
    positions = pd.concat(position_rows, ignore_index=True)
    return daily, positions


def add_cost_returns(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in daily.itertuples(index=False):
        for cost_bps in COSTS_BPS:
            cost = 2 * (cost_bps / 10_000) * (row.gross_exposure if row.strategy_day_available else np.nan)
            rows.append({
                "sample": row.sample, "strategy": row.strategy, "signal_date": row.signal_date, "trade_date": row.trade_date,
                "strategy_day_available": row.strategy_day_available, "one_way_cost_bps": cost_bps,
                "gross_return": row.gross_return, "round_trip_cost": cost,
                "net_return": row.gross_return - cost if row.strategy_day_available else np.nan,
            })
    return pd.DataFrame(rows)


def summary_table(returns: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (sample, strategy, cost_bps), group in returns.groupby(["sample", "strategy", "one_way_cost_bps"], sort=True):
        for return_column, label in [("gross_return", "gross"), ("net_return", "net")]:
            stat = performance_stats(group.loc[group["strategy_day_available"], return_column])
            stat.update({"sample": sample, "strategy": strategy, "portfolio_specification": "continuous_score" if strategy != "S1_top_bottom_decile" else "equal_weight_top_decile_minus_bottom_decile", "return_type": label, "one_way_cost_bps": cost_bps, "unavailable_strategy_days": int((~group["strategy_day_available"]).sum()), "formed_strategy_days": int(group["strategy_day_formed"].sum()) if "strategy_day_formed" in group else np.nan})
            rows.append(stat)
    return pd.DataFrame(rows)


def subperiods(sample: str) -> list[tuple[str, str, str]]:
    if sample.startswith("original"):
        return [("predefined_subperiod_1", "2025-05-28", "2026-01-13"), ("predefined_subperiod_2", "2026-01-14", "2026-08-31")]
    return [("not_predefined_for_additional_sample", *SAMPLES[sample])]


def calendar_and_subperiod_tables(returns: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    calendar, subperiod = [], []
    for (sample, strategy, cost_bps), group in returns.loc[returns.strategy_day_available].groupby(["sample", "strategy", "one_way_cost_bps"]):
        group = group.copy(); group["year"] = pd.to_datetime(group["signal_date"]).dt.year
        for year, values in group.groupby("year"):
            stat = performance_stats(values["net_return"])
            calendar.append({"sample": sample, "strategy": strategy, "one_way_cost_bps": cost_bps, "year": int(year), **stat})
        for name, start, end in subperiods(sample):
            values = group.loc[group["signal_date"].between(start, end), "net_return"]
            subperiod.append({"sample": sample, "strategy": strategy, "one_way_cost_bps": cost_bps, "subperiod": name, "start": start, "end": end, **performance_stats(values)})
    return pd.DataFrame(calendar), pd.DataFrame(subperiod)


def paired_tables(returns: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, paired_daily = [], []
    for sample in SAMPLES:
        for cost_bps in COSTS_BPS:
            wide = returns.loc[(returns["sample"] == sample) & (returns["one_way_cost_bps"] == cost_bps) & returns["strategy"].isin(["S0_continuous", "S1_continuous", "S2_continuous"]), ["signal_date", "strategy", "net_return"]].pivot(index="signal_date", columns="strategy", values="net_return")
            common = wide.dropna(subset=["S0_continuous", "S1_continuous", "S2_continuous"])
            for benchmark, label in [("S0_continuous", "S1_minus_S0"), ("S2_continuous", "S1_minus_S2")]:
                difference = common["S1_continuous"] - common[benchmark]
                rows.append({"sample": sample, "one_way_cost_bps": cost_bps, "comparison": label, "paired_days": len(difference), **performance_stats(difference)})
            common = common.reset_index()
            for strategy in ["S0_continuous", "S1_continuous", "S2_continuous"]:
                paired_daily.append(pd.DataFrame({"sample": sample, "one_way_cost_bps": cost_bps, "signal_date": common["signal_date"], "strategy": strategy, "net_return": common[strategy]}))
    return pd.DataFrame(rows), pd.concat(paired_daily, ignore_index=True)


def capacity_table(positions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sample, group in positions.loc[(positions["strategy"] == "S1_continuous") & positions["nonzero_position"]].groupby("sample"):
        valid = group.loc[group["prior_median_dollar_volume_20"].gt(0)].copy()
        for gross_usd in (10_000_000, 50_000_000):
            participation = gross_usd * valid["weight"].abs() / valid["prior_median_dollar_volume_20"]
            rows.append({"sample": sample, "strategy": "S1_continuous", "hypothetical_gross_portfolio_usd": gross_usd, "nonzero_positions": len(group), "positions_with_valid_prior_adv": len(valid), "positions_missing_prior_adv": len(group) - len(valid), "median_participation": participation.median(), "p95_participation": participation.quantile(.95), "share_positions_over_1pct": float((participation > .01).mean()), "share_positions_over_5pct": float((participation > .05).mean()), "share_positions_over_10pct": float((participation > .10).mean())})
    return pd.DataFrame(rows)


def globe_life_table(daily: pd.DataFrame, positions: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    rows = []
    gl = positions.loc[(positions["Date"] == GL_DATE) & (positions["canonical_research_symbol"] == GL_SECURITY) & positions["nonzero_position"]].copy()
    for row in gl.itertuples(index=False):
        day = daily.loc[(daily["sample"] == row.sample) & (daily["strategy"] == row.strategy) & (daily["signal_date"] == GL_DATE)].iloc[0]
        rows.append({"sample": row.sample, "strategy": row.strategy, "signal_date": GL_DATE, "trade_date": row.designated_target_date, "canonical_research_symbol": GL_SECURITY, "weight": row.weight, "forward_oc_return": row.forward_oc_return, "portfolio_return_contribution": row.weight * row.forward_oc_return, "strategy_gross_return": day.gross_return, "in_nonzero_position": True})
    # Labeled sensitivity: omit only the affected strategy day; never reweight or replace primary results.
    for (sample, strategy, cost_bps), group in returns.groupby(["sample", "strategy", "one_way_cost_bps"]):
        if sample.startswith("additional") and strategy == "S1_continuous":
            primary = performance_stats(group.loc[group.strategy_day_available, "net_return"])
            sensitivity = performance_stats(group.loc[group.strategy_day_available & group.signal_date.ne(GL_DATE), "net_return"])
            rows.append({"sample": sample, "strategy": strategy, "one_way_cost_bps": cost_bps, "sensitivity": "exclude_only_GL_affected_strategy_day_nonprimary", "primary_cumulative_return": primary["cumulative_return"], "sensitivity_cumulative_return": sensitivity["cumulative_return"], "primary_mean_daily_bps": primary["mean_daily_return_bps"], "sensitivity_mean_daily_bps": sensitivity["mean_daily_return_bps"], "primary_hac5_t": primary["hac5_t"], "sensitivity_hac5_t": sensitivity["hac5_t"]})
    return pd.DataFrame(rows)


def make_figures(figures: Path, returns: pd.DataFrame, paired: pd.DataFrame, calendar: pd.DataFrame) -> None:
    figures.mkdir(parents=True, exist_ok=True)
    primary = returns.loc[(returns["strategy"] == "S1_continuous") & returns.strategy_day_available].copy()
    for sample, group in primary.groupby("sample"):
        short = "additional" if sample.startswith("additional") else "original"
        plt.figure(figsize=(8, 4))
        for column, label, color in [("gross_return", "Gross", "#2468a2"), ("net_return", "Net, 2.5 bps/side", "#c44e52")]:
            series = group.loc[group.one_way_cost_bps.eq(PRIMARY_COST_BPS) if column == "net_return" else group.one_way_cost_bps.eq(0), ["signal_date", column]].sort_values("signal_date")
            plt.plot(series["signal_date"], (1 + series[column]).cumprod() - 1, label=label, color=color)
        plt.axhline(0, color="black", lw=.6); plt.legend(); plt.ylabel("Cumulative return"); plt.title(f"S1 continuous: {short}"); plt.tight_layout(); plt.savefig(figures / f"phase10_{short}_s1_gross_net_cumulative.png", dpi=150); plt.close()
        net = group.loc[group.one_way_cost_bps.eq(PRIMARY_COST_BPS)].sort_values("signal_date").copy()
        cumulative = (1 + net.net_return).cumprod(); dd = cumulative / cumulative.cummax() - 1
        plt.figure(figsize=(8, 3.5)); plt.fill_between(net.signal_date, dd, 0, color="#c44e52", alpha=.55); plt.ylabel("Drawdown"); plt.title(f"S1 primary-net drawdown: {short}"); plt.tight_layout(); plt.savefig(figures / f"phase10_{short}_s1_drawdown.png", dpi=150); plt.close()
        rolling = net.net_return.rolling(63).mean() / net.net_return.rolling(63).std(ddof=1) * np.sqrt(252)
        gross = group.loc[group.one_way_cost_bps.eq(0)].sort_values("signal_date").gross_return
        rolling_gross = gross.rolling(63).mean() / gross.rolling(63).std(ddof=1) * np.sqrt(252)
        plt.figure(figsize=(8, 3.5)); plt.plot(net.signal_date, rolling_gross, label="Gross", color="#2468a2"); plt.plot(net.signal_date, rolling, label="Net, 2.5 bps/side", color="#c44e52"); plt.axhline(0, color="black", lw=.6); plt.legend(); plt.ylabel("63-day Sharpe"); plt.title(f"S1 rolling Sharpe: {short}"); plt.tight_layout(); plt.savefig(figures / f"phase10_{short}_s1_rolling_63d_sharpe.png", dpi=150); plt.close()
        plt.figure(figsize=(7, 3.5)); plt.hist(net.net_return * 10_000, bins=35, color="#2468a2", alpha=.8); plt.axvline(0, color="black", lw=.6); plt.xlabel("Daily primary-net return (bps)"); plt.title(f"S1 daily-return distribution: {short}"); plt.tight_layout(); plt.savefig(figures / f"phase10_{short}_s1_daily_return_distribution.png", dpi=150); plt.close()
    for sample, group in paired.loc[paired.one_way_cost_bps.eq(PRIMARY_COST_BPS)].groupby("sample"):
        short = "additional" if sample.startswith("additional") else "original"
        plt.figure(figsize=(8, 4))
        for strategy, values in group.groupby("strategy"):
            values = values.sort_values("signal_date")
            plt.plot(values.signal_date, (1 + values.net_return).cumprod() - 1, label=strategy.replace("_continuous", ""))
        plt.axhline(0, color="black", lw=.6); plt.legend(); plt.ylabel("Cumulative primary-net return"); plt.title(f"Paired continuous strategies: {short}"); plt.tight_layout(); plt.savefig(figures / f"phase10_{short}_paired_primary_net_cumulative.png", dpi=150); plt.close()
    cost = returns.loc[(returns.strategy == "S1_continuous") & returns.strategy_day_available].groupby(["sample", "one_way_cost_bps"], as_index=False).agg(mean_daily_return=("net_return", "mean"))
    plt.figure(figsize=(7, 4))
    for sample, values in cost.groupby("sample"):
        plt.plot(values.one_way_cost_bps, values.mean_daily_return * 10_000, "o-", label="Additional" if sample.startswith("additional") else "Original")
    plt.axhline(0, color="black", lw=.6); plt.xlabel("One-way cost (bps)"); plt.ylabel("Mean daily net return (bps)"); plt.legend(); plt.tight_layout(); plt.savefig(figures / "phase10_s1_transaction_cost_sensitivity.png", dpi=150); plt.close()
    years = calendar.loc[(calendar.strategy == "S1_continuous") & calendar.one_way_cost_bps.eq(PRIMARY_COST_BPS)]
    plt.figure(figsize=(7, 4)); labels = years["sample"].str.startswith("additional").map({True: "Additional", False: "Original"}) + " " + years["year"].astype(str); plt.bar(labels, years.annualized_compounded_return * 100, color="#2468a2"); plt.xticks(rotation=35, ha="right"); plt.ylabel("Annualized compounded return (%)"); plt.title("S1 primary-net calendar-year results"); plt.tight_layout(); plt.savefig(figures / "phase10_s1_calendar_year_returns.png", dpi=150); plt.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args(); root = args.root.resolve()
    manifest, source_count = create_or_validate_source_manifest(root)
    panel = pd.read_parquet(root / "data/processed/phase9_final_rank_score_panel.parquet")
    panel["Date"] = pd.to_datetime(panel["Date"]); panel["designated_target_date"] = pd.to_datetime(panel["designated_target_date"])
    if panel.duplicated(["sample", "Date", "canonical_research_symbol"]).any():
        raise AssertionError("Duplicate score-panel key")
    if panel.groupby(["sample", "Date"]).size().ne(400).any():
        raise AssertionError("Phase 9 top-400 membership does not reproduce")
    target_mapping = panel.groupby(["sample", "Date"])["designated_target_date"].agg(["nunique", "min"])
    if not target_mapping["nunique"].eq(1).all() or not (target_mapping["min"].to_numpy() > target_mapping.index.get_level_values("Date").to_numpy()).all():
        raise AssertionError("The Phase 9 designated target mapping is not one shared strictly-later session per signal date")
    panel = add_prior_adv(root, panel)
    strategies = [("S0_continuous", "S0_bounded_rank_score"), ("S1_continuous", "final_rank_score"), ("S2_continuous", "S2_bounded_rank_score"), ("S1_top_bottom_decile", None)]
    daily_parts, position_parts = [], []
    for strategy, score in strategies:
        daily, positions = form_strategy_days(panel, strategy, score)
        daily_parts.append(daily); position_parts.append(positions)
    daily = pd.concat(daily_parts, ignore_index=True); positions = pd.concat(position_parts, ignore_index=True)
    returns = add_cost_returns(daily).merge(daily[["sample", "strategy", "signal_date", "strategy_day_formed"]], on=["sample", "strategy", "signal_date"], how="left", validate="many_to_one")
    performance = summary_table(returns, daily)
    calendar, subperiod = calendar_and_subperiod_tables(returns)
    paired_summary, paired_daily = paired_tables(returns)
    capacity = capacity_table(positions)
    globe = globe_life_table(daily, positions, returns)
    tables = root / "results/tables"; processed = root / "data/processed"; figures = root / "results/figures"
    daily.to_parquet(processed / "phase10_daily_portfolio_exposure_panel.parquet", index=False)
    positions.to_parquet(processed / "phase10_portfolio_position_panel.parquet", index=False)
    returns.to_parquet(processed / "phase10_daily_portfolio_returns_by_cost.parquet", index=False)
    performance.to_csv(tables / "phase10_performance_summary.csv", index=False)
    calendar.to_csv(tables / "phase10_calendar_year_results.csv", index=False)
    subperiod.to_csv(tables / "phase10_subperiod_results.csv", index=False)
    paired_summary.to_csv(tables / "phase10_paired_comparisons.csv", index=False)
    paired_daily.to_csv(tables / "phase10_paired_daily_returns.csv", index=False)
    capacity.to_csv(tables / "phase10_capacity_diagnostics.csv", index=False)
    globe.to_csv(tables / "phase10_globe_life_diagnostic_and_sensitivity.csv", index=False)
    unavailable = daily.loc[~daily.strategy_day_available].copy()
    unavailable.to_csv(tables / "phase10_unavailable_strategy_days.csv", index=False)
    daily.to_csv(tables / "phase10_daily_position_exposure_diagnostics.csv", index=False)
    make_figures(figures, returns, paired_daily, calendar)
    _, source_verified = create_or_validate_source_manifest(root)
    print(json.dumps({"daily_strategy_rows": len(daily), "position_rows": len(positions), "available_strategy_days": int(daily.strategy_day_available.sum()), "unavailable_strategy_days": int((~daily.strategy_day_available).sum()), "source_artifacts_verified": source_verified, "source_manifest": str(manifest.relative_to(root))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
