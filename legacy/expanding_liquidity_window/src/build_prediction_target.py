"""Build Phase 4 next-shared-session adjusted open-to-close targets only."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yfinance as yf


VALUE_COLUMNS = ["Open", "Close", "Adj Close", "Dividends", "Stock Splits"]


def acquire_next_session(symbols: pd.DataFrame, start: str, end: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retrieve one required session; preserve a per-symbol success/failure log."""
    frames, logs = [], []
    for offset in range(0, len(symbols), 50):
        batch = symbols.iloc[offset : offset + 50]
        tickers = batch.yahoo_symbol.tolist()
        try:
            data = yf.download(tickers, start=start, end=end, auto_adjust=False, actions=True, group_by="column", progress=False, threads=True, timeout=45)
        except Exception as exc:
            for row in batch.itertuples():
                logs.append({"canonical_research_symbol": row.canonical_research_symbol, "yahoo_symbol": row.yahoo_symbol, "status": "download_exception", "detail": f"{type(exc).__name__}: {exc}", "rows": 0})
            continue
        for row in batch.itertuples():
            try:
                frame = data.xs(row.yahoo_symbol, axis=1, level="Ticker", drop_level=True).dropna(how="all")
                frame = frame[VALUE_COLUMNS]
            except Exception as exc:
                logs.append({"canonical_research_symbol": row.canonical_research_symbol, "yahoo_symbol": row.yahoo_symbol, "status": "ticker_absent_or_schema_failure", "detail": f"{type(exc).__name__}: {exc}", "rows": 0})
                continue
            if frame.empty:
                logs.append({"canonical_research_symbol": row.canonical_research_symbol, "yahoo_symbol": row.yahoo_symbol, "status": "no_rows", "detail": "", "rows": 0})
                continue
            frame.index.name = "Date"
            frame = frame.reset_index()
            frame["Date"] = pd.to_datetime(frame["Date"]).dt.tz_localize(None)
            frame["canonical_research_symbol"] = row.canonical_research_symbol
            frame["yahoo_symbol"] = row.yahoo_symbol
            frames.append(frame)
            logs.append({"canonical_research_symbol": row.canonical_research_symbol, "yahoo_symbol": row.yahoo_symbol, "status": "success", "detail": "", "rows": len(frame)})
    return (pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()), pd.DataFrame(logs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--tables-dir", type=Path, default=Path("results/tables"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    args = parser.parse_args()
    panel = pd.read_parquet(args.processed_dir / "master_stock_day_panel.parquet")
    panel["Date"] = pd.to_datetime(panel["Date"])
    panel["signal_date"] = panel["Date"]
    market = pd.read_csv(args.processed_dir / "prototype_market_panel.csv", parse_dates=["Date"])
    aug_members = panel.loc[panel["Date"] == pd.Timestamp("2026-08-31"), ["canonical_research_symbol", "market_yahoo_symbol"]].drop_duplicates()
    aug_members = aug_members.rename(columns={"market_yahoo_symbol": "yahoo_symbol"})
    next_session, log = acquire_next_session(aug_members, "2026-09-01", "2026-09-02")
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    args.tables_dir.mkdir(parents=True, exist_ok=True)
    retrieval = datetime.now(UTC).isoformat()
    next_session.to_csv(args.raw_dir / "yahoo_target_extension_20260901.csv", index=False)
    log.to_csv(args.tables_dir / "phase4_yahoo_extension_download_log.csv", index=False)
    if not next_session.empty:
        next_session["adjustment_factor"] = next_session["Adj Close"] / next_session["Close"]
        next_session["adjusted_open"] = next_session["Open"] * next_session["adjustment_factor"]
        next_session["adjusted_close"] = next_session["Adj Close"]
    market = market.rename(columns={"source_symbol": "canonical_research_symbol", "yahoo_symbol": "market_yahoo_symbol"})
    extension = next_session.rename(columns={"yahoo_symbol": "market_yahoo_symbol"})
    all_market = pd.concat([market, extension], ignore_index=True, sort=False)
    calendar = all_market.Date.drop_duplicates().sort_values().reset_index(drop=True)
    calendar_map = pd.DataFrame({"Date": calendar, "designated_target_date": calendar.shift(-1)}).dropna()
    panel = panel.merge(calendar_map, on="Date", how="left", validate="many_to_one")
    prices = all_market[["Date", "canonical_research_symbol", "adjusted_open", "adjusted_close", "Stock Splits", "Dividends"]].rename(columns={
        "Date": "designated_target_date", "adjusted_open": "next_session_adjusted_open", "adjusted_close": "next_session_adjusted_close",
        "Stock Splits": "next_session_stock_splits", "Dividends": "next_session_dividends"})
    panel = panel.merge(prices, on=["designated_target_date", "canonical_research_symbol"], how="left", validate="many_to_one")
    panel["forward_oc_return"] = panel["next_session_adjusted_close"] / panel["next_session_adjusted_open"] - 1
    panel["target_status"] = "available"
    panel.loc[panel["designated_target_date"].isna(), "target_status"] = "no_next_shared_market_session"
    panel.loc[panel["designated_target_date"].notna() & panel["next_session_adjusted_open"].isna(), "target_status"] = "missing_designated_next_session_market_observation"
    panel.loc[(panel["next_session_adjusted_open"] <= 0) | (panel["next_session_adjusted_close"] <= 0), "target_status"] = "invalid_nonpositive_next_session_price"
    panel.loc[~pd.Series(panel["forward_oc_return"]).map(lambda x: pd.notna(x) and float("-inf") < x < float("inf")), "target_status"] = panel["target_status"].where(panel["target_status"] != "available", "nonfinite_forward_return")
    panel["target_available"] = panel["target_status"].eq("available")
    panel["in_locked_primary_evaluation_window"] = panel["Date"].between("2025-05-28", "2026-08-31")
    if panel.duplicated(["Date", "canonical_research_symbol"]).any():
        raise ValueError("target panel duplicate key")
    panel.to_parquet(args.processed_dir / "master_stock_day_with_target.parquet", index=False)
    panel.to_csv(args.processed_dir / "master_stock_day_with_target.csv", index=False)
    overall = panel.groupby("target_status", as_index=False).size().rename(columns={"size": "rows"})
    by_date = panel.groupby(["Date", "target_status"], as_index=False).size().rename(columns={"size": "rows"})
    by_security = panel.groupby(["canonical_research_symbol", "target_status"], as_index=False).size().rename(columns={"size": "rows"})
    extreme = panel.loc[panel["forward_oc_return"].abs() >= .25, ["Date", "canonical_research_symbol", "designated_target_date", "forward_oc_return", "next_session_stock_splits", "next_session_dividends"]]
    overall.to_csv(args.tables_dir / "phase4_target_coverage_overall.csv", index=False)
    by_date.to_csv(args.tables_dir / "phase4_target_coverage_by_date.csv", index=False)
    by_security.to_csv(args.tables_dir / "phase4_target_coverage_by_security.csv", index=False)
    extreme.to_csv(args.tables_dir / "phase4_extreme_forward_oc_returns.csv", index=False)
    (args.processed_dir / "phase4_target_metadata.json").write_text(json.dumps({"extension_retrieved_at_utc": retrieval, "extension_rows": len(next_session), "extension_successes": int((log.status=='success').sum()), "extension_failures": int((log.status!='success').sum())}, indent=2)+"\n")
    print(f"panel_rows={len(panel)}; targets={int(panel.target_available.sum())}; extension_rows={len(next_session)}")


if __name__ == "__main__":
    raise SystemExit(main())
