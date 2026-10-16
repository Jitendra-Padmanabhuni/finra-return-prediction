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
    parser.add_argument(
        "--existing-extension",
        type=Path,
        help="Reuse an immutable prior 2026-09-01 extract and download only newly required symbols",
    )
    args = parser.parse_args()
    panel = pd.read_parquet(args.processed_dir / "master_stock_day_panel.parquet")
    panel["Date"] = pd.to_datetime(panel["Date"])
    panel["signal_date"] = panel["Date"]
    market = pd.read_csv(args.processed_dir / "prototype_market_panel.csv", parse_dates=["Date"])
    aug_members = panel.loc[panel["Date"] == pd.Timestamp("2026-08-31"), ["canonical_research_symbol", "market_yahoo_symbol"]].drop_duplicates()
    aug_members = aug_members.rename(columns={"market_yahoo_symbol": "yahoo_symbol"})
    reused = pd.DataFrame()
    reused_log = pd.DataFrame()
    if args.existing_extension:
        reused = pd.read_csv(args.existing_extension, parse_dates=["Date"])
        reused = reused.merge(aug_members, on=["canonical_research_symbol", "yahoo_symbol"], how="inner", validate="many_to_one")
        reused_log = aug_members.loc[aug_members["canonical_research_symbol"].isin(reused["canonical_research_symbol"])].copy()
        reused_log["status"] = "reused_immutable_existing_extension"
        reused_log["detail"] = str(args.existing_extension)
        reused_log["rows"] = 1
    missing_members = aug_members.loc[~aug_members["canonical_research_symbol"].isin(reused.get("canonical_research_symbol", pd.Series(dtype=str)))]
    downloaded, download_log = acquire_next_session(missing_members, "2026-09-01", "2026-09-02") if len(missing_members) else (pd.DataFrame(), pd.DataFrame())
    next_session = pd.concat([reused, downloaded], ignore_index=True, sort=False)
    log = pd.concat([reused_log, download_log], ignore_index=True, sort=False)
    if next_session.duplicated(["Date", "canonical_research_symbol"]).any():
        raise ValueError("Duplicate corrected target-extension key")
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    args.tables_dir.mkdir(parents=True, exist_ok=True)
    retrieval = datetime.now(UTC).isoformat()
    extension_name = "yahoo_target_extension_20260901_corrected.csv" if args.existing_extension else "yahoo_target_extension_20260901.csv"
    next_session.to_csv(args.raw_dir / extension_name, index=False)
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
    (args.processed_dir / "phase4_target_metadata.json").write_text(json.dumps({
        "extension_retrieved_at_utc": retrieval,
        "extension_rows": len(next_session),
        "extension_reused_rows": len(reused),
        "extension_new_download_rows": len(downloaded),
        "extension_successes": int(log.status.isin(["success", "reused_immutable_existing_extension"]).sum()),
        "extension_failures": int((~log.status.isin(["success", "reused_immutable_existing_extension"])).sum()),
        "source_file": extension_name,
    }, indent=2)+"\n")
    print(f"panel_rows={len(panel)}; targets={int(panel.target_available.sum())}; extension_rows={len(next_session)}")


if __name__ == "__main__":
    raise SystemExit(main())
