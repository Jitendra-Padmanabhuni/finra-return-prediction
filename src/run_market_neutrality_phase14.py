"""Phase 14 single-factor market-model (CAPM-style) regression on the frozen
Phase 10 continuous dollar-neutral portfolios, original sample only.

This phase does not rebuild, re-derive, or re-weight any Phase 10 portfolio.
It reads the exact frozen daily return series already computed and pins the
Phase 10 artifacts it consumes as unchanged, immutable source artifacts.

Market factor: SPY (a traded security, not the raw index) via yfinance,
market_return[t] = adjusted_close[t] / adjusted_open[t] - 1, the same
same-session open-to-close construction as Phase 4's forward_oc_return and
the strategy's own no-overnight holding window, over the exact same available
trade dates as each strategy's original-sample gross return series.

Regression: strategy_gross_return[t] = alpha + beta * market_return[t] + eps[t],
statsmodels OLS on [constant, market_return], cov_type="HAC", maxlags=5.
Alpha is the primary, decisive one-sided test (H0: alpha <= 0, t >= 1.645).
Beta is a two-sided diagnostic only (H0: beta = 0), not a pass/fail gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import yfinance as yf
from scipy import stats

HAC_LAGS = 5
ALPHA_CRITICAL_VALUE = 1.645
ORIGINAL_SAMPLE = "original_2025-05-28_2026-08-31"
ORIGINAL_START, ORIGINAL_END = "2025-05-28", "2026-08-31"
STRATEGIES = ["S0_continuous", "S1_continuous", "S2_continuous"]
SECONDARY_NET_ONE_WAY_COST_BPS = 2.5
MARKET_INSTRUMENT = "SPY"


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_artifact_paths(root: Path) -> list[Path]:
    """Phase 10 artifacts this phase consumes, verbatim and unmodified."""
    explicit = [
        root / "data/processed/phase10_daily_portfolio_exposure_panel.parquet",
        root / "data/processed/phase10_daily_portfolio_returns_by_cost.parquet",
        root / "docs/phase10_report.md",
        root / "src/run_realistic_backtest_phase10.py",
        root / "tests/test_phase10_backtest.py",
    ]
    tables = sorted((root / "results/tables").glob("phase10_*"))
    return sorted(set(explicit + tables))


def create_or_validate_source_manifest(root: Path) -> tuple[Path, int]:
    """Hash the immutable Phase 10 source artifacts this phase consumes."""
    manifest = root / "preservation/phase14_pre_market_neutrality_source_artifacts/SHA256SUMS.txt"
    paths = source_artifact_paths(root)
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing Phase 14 source artifacts: {missing}")
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
        raise AssertionError(f"Phase 14 source artifact hash mismatch: {failures}")
    return manifest, len(paths)


def load_strategy_returns(root: Path) -> pd.DataFrame:
    """Exact frozen Phase 10 original-sample gross + primary-net returns; no recomputation."""
    exposure = pd.read_parquet(root / "data/processed/phase10_daily_portfolio_exposure_panel.parquet")
    by_cost = pd.read_parquet(root / "data/processed/phase10_daily_portfolio_returns_by_cost.parquet")

    gross = exposure.loc[
        (exposure["sample"] == ORIGINAL_SAMPLE) & exposure["strategy"].isin(STRATEGIES) & exposure["strategy_day_available"]
    ][["strategy", "trade_date", "gross_return"]].copy()

    net = by_cost.loc[
        (by_cost["sample"] == ORIGINAL_SAMPLE)
        & by_cost["strategy"].isin(STRATEGIES)
        & by_cost["strategy_day_available"]
        & np.isclose(by_cost["one_way_cost_bps"], SECONDARY_NET_ONE_WAY_COST_BPS)
    ][["strategy", "trade_date", "net_return"]].copy()

    merged = gross.merge(net, on=["strategy", "trade_date"], how="left", validate="one_to_one")
    merged["trade_date"] = pd.to_datetime(merged["trade_date"])
    return merged.sort_values(["strategy", "trade_date"]).reset_index(drop=True)


def acquire_spy(root: Path, start: str, end_inclusive: str) -> tuple[pd.DataFrame, dict]:
    """Acquire raw SPY OHLC/adjusted-close/actions; save raw file with retrieval metadata."""
    end_exclusive = (pd.Timestamp(end_inclusive) + pd.Timedelta(days=3)).strftime("%Y-%m-%d")
    retrieval_ts = datetime.now(UTC).isoformat()
    data = yf.download(MARKET_INSTRUMENT, start=start, end=end_exclusive, auto_adjust=False, actions=True, progress=False, timeout=45)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data = data.reset_index()
    data["Date"] = pd.to_datetime(data["Date"]).dt.tz_localize(None)

    raw_dir = root / "data/raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    ts_slug = retrieval_ts.replace(":", "").replace("-", "").split(".")[0]
    raw_path = raw_dir / f"spy_market_factor_{start}_{end_inclusive}_{ts_slug}.csv"
    data.to_csv(raw_path, index=False)

    log = {
        "symbol": MARKET_INSTRUMENT,
        "requested_start": start,
        "requested_end_inclusive": end_inclusive,
        "download_end_exclusive": end_exclusive,
        "retrieval_timestamp_utc": retrieval_ts,
        "rows_returned": len(data),
        "auto_adjust": False,
        "raw_path": str(raw_path.relative_to(root)),
        "yfinance_version": yf.__version__,
    }
    return data, log


def build_market_factor(spy_raw: pd.DataFrame) -> pd.DataFrame:
    frame = spy_raw.copy()
    frame["adjustment_factor"] = frame["Adj Close"] / frame["Close"]
    frame["adjusted_open"] = frame["Open"] * frame["adjustment_factor"]
    frame["adjusted_close"] = frame["Adj Close"]
    frame["market_return"] = frame["adjusted_close"] / frame["adjusted_open"] - 1
    frame = frame.rename(columns={"Date": "trade_date"})
    return frame[["trade_date", "Open", "Close", "Adj Close", "adjustment_factor", "adjusted_open", "adjusted_close", "market_return"]]


def coverage_check(strategy_returns: pd.DataFrame, market_factor: pd.DataFrame) -> pd.DataFrame:
    """Document any strategy trade date missing from the SPY market factor series."""
    market_dates = set(market_factor["trade_date"])
    rows = []
    for strategy, group in strategy_returns.groupby("strategy"):
        strategy_dates = set(group["trade_date"])
        missing = sorted(strategy_dates - market_dates)
        rows.append({
            "strategy": strategy,
            "strategy_trade_dates": len(strategy_dates),
            "spy_trade_dates_in_window": len(market_dates),
            "missing_from_spy": len(missing),
            "missing_dates": ";".join(d.strftime("%Y-%m-%d") for d in missing),
        })
    return pd.DataFrame(rows)


def market_model_stats(strategy_returns: pd.Series, market_returns: pd.Series) -> dict[str, float]:
    y = strategy_returns.astype(float).to_numpy()
    x = sm.add_constant(market_returns.astype(float).to_numpy())
    fit = sm.OLS(y, x).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})
    alpha, beta = float(fit.params[0]), float(fit.params[1])
    alpha_se, beta_se = float(fit.bse[0]), float(fit.bse[1])
    alpha_t, beta_t = float(fit.tvalues[0]), float(fit.tvalues[1])
    return {
        "n": len(y),
        "alpha": alpha,
        "alpha_hac5_se": alpha_se,
        "alpha_hac5_t": alpha_t,
        "alpha_one_sided_p_greater_zero": float(stats.norm.sf(alpha_t)),
        "alpha_clears_primary_bar_1_645": bool(alpha_t >= ALPHA_CRITICAL_VALUE),
        "beta": beta,
        "beta_hac5_se": beta_se,
        "beta_hac5_t": beta_t,
        "beta_two_sided_p": float(2 * stats.norm.sf(abs(beta_t))),
        "beta_flag_large_or_significant": bool(abs(beta) >= 0.10 or (2 * stats.norm.sf(abs(beta_t))) < 0.05),
        "r_squared": float(fit.rsquared),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--tables-dir", type=Path, default=Path("results/tables"))
    parser.add_argument("--figures-dir", type=Path, default=Path("results/figures"))
    args = parser.parse_args()
    root = args.root.resolve()
    args.tables_dir.mkdir(parents=True, exist_ok=True)
    args.figures_dir.mkdir(parents=True, exist_ok=True)

    manifest, source_count = create_or_validate_source_manifest(root)

    strategy_returns = load_strategy_returns(root)
    window_start = (strategy_returns["trade_date"].min() - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
    window_end = strategy_returns["trade_date"].max().strftime("%Y-%m-%d")

    spy_raw, download_log = acquire_spy(root, window_start, window_end)
    market_factor = build_market_factor(spy_raw)

    coverage = coverage_check(strategy_returns, market_factor)

    results_rows = []
    for strategy in STRATEGIES:
        strat = strategy_returns.loc[strategy_returns["strategy"] == strategy]
        aligned = strat.merge(market_factor[["trade_date", "market_return"]], on="trade_date", how="inner")
        gross_stats = market_model_stats(aligned["gross_return"], aligned["market_return"])
        gross_stats.update({"strategy": strategy, "return_type": "gross", "one_way_cost_bps": 0.0})
        results_rows.append(gross_stats)

        net_aligned = aligned.dropna(subset=["net_return"])
        net_stats = market_model_stats(net_aligned["net_return"], net_aligned["market_return"])
        net_stats.update({"strategy": strategy, "return_type": "net", "one_way_cost_bps": SECONDARY_NET_ONE_WAY_COST_BPS})
        results_rows.append(net_stats)

    results = pd.DataFrame(results_rows)
    column_order = ["strategy", "return_type", "one_way_cost_bps", "n", "alpha", "alpha_hac5_se", "alpha_hac5_t",
                     "alpha_one_sided_p_greater_zero", "alpha_clears_primary_bar_1_645", "beta", "beta_hac5_se",
                     "beta_hac5_t", "beta_two_sided_p", "beta_flag_large_or_significant", "r_squared"]
    results = results[column_order]

    market_factor.to_csv(args.tables_dir / "phase14_spy_market_factor.csv", index=False)
    coverage.to_csv(args.tables_dir / "phase14_spy_coverage_check.csv", index=False)
    pd.DataFrame([download_log]).to_csv(args.tables_dir / "phase14_spy_download_log.csv", index=False)
    results.to_csv(args.tables_dir / "phase14_market_model_results.csv", index=False)
    strategy_returns.to_csv(args.tables_dir / "phase14_strategy_returns_used.csv", index=False)

    for strategy in STRATEGIES:
        strat = strategy_returns.loc[strategy_returns["strategy"] == strategy]
        aligned = strat.merge(market_factor[["trade_date", "market_return"]], on="trade_date", how="inner")
        row = results.loc[(results.strategy == strategy) & (results.return_type == "gross")].iloc[0]
        plt.figure(figsize=(5, 4.2))
        plt.scatter(aligned["market_return"], aligned["gross_return"], s=10, alpha=0.5, color="#2455a6")
        xs = np.linspace(aligned["market_return"].min(), aligned["market_return"].max(), 50)
        plt.plot(xs, row["alpha"] + row["beta"] * xs, color="#9b4d2b", lw=1.5)
        plt.axhline(0, color="black", lw=.5); plt.axvline(0, color="black", lw=.5)
        plt.xlabel("SPY same-session open-to-close return")
        plt.ylabel(f"{strategy} gross daily return")
        plt.title(f"{strategy}: alpha={row['alpha']*1e4:.2f}bp (t={row['alpha_hac5_t']:.2f}), beta={row['beta']:.3f} (t={row['beta_hac5_t']:.2f})")
        plt.tight_layout()
        plt.savefig(args.figures_dir / f"phase14_{strategy}_market_model_scatter.png", dpi=150)
        plt.close()

    print(json.dumps({"source_artifacts_verified": source_count, "spy_download_log": download_log, "coverage": coverage.to_dict(orient="records"), "results": results.to_dict(orient="records")}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
