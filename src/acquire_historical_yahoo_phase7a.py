"""Acquire missing Phase 7A Yahoo history while reusing existing observations."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yfinance as yf


VALUE_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Splits"]


def download_group(tickers: list[str], start: str, end: str, batch_size: int) -> tuple[list[pd.DataFrame], list[dict[str, object]]]:
    frames: list[pd.DataFrame] = []
    logs: list[dict[str, object]] = []
    for batch_number, offset in enumerate(range(0, len(tickers), batch_size), start=1):
        batch = tickers[offset : offset + batch_size]
        try:
            data = yf.download(batch, start=start, end=end, auto_adjust=False, actions=True, group_by="column", progress=False, threads=True, timeout=45)
        except Exception as exc:
            for ticker in batch:
                logs.append({"yahoo_symbol": ticker, "start": start, "end_exclusive": end, "batch": batch_number, "status": "download_exception", "detail": f"{type(exc).__name__}: {exc}", "rows": 0})
            continue
        for ticker in batch:
            try:
                frame = data.xs(ticker, axis=1, level="Ticker", drop_level=True).dropna(how="all")
                missing = [column for column in VALUE_COLUMNS if column not in frame.columns]
                if missing:
                    raise KeyError(f"missing columns {missing}")
                frame = frame[VALUE_COLUMNS].copy()
            except Exception as exc:
                logs.append({"yahoo_symbol": ticker, "start": start, "end_exclusive": end, "batch": batch_number, "status": "ticker_absent_or_schema_failure", "detail": f"{type(exc).__name__}: {exc}", "rows": 0})
                continue
            if frame.empty:
                logs.append({"yahoo_symbol": ticker, "start": start, "end_exclusive": end, "batch": batch_number, "status": "no_rows", "detail": "", "rows": 0})
                continue
            frame.index.name = "Date"; frame = frame.reset_index(); frame["Date"] = pd.to_datetime(frame["Date"]).dt.tz_localize(None); frame["yahoo_symbol"] = ticker
            frames.append(frame)
            logs.append({"yahoo_symbol": ticker, "start": start, "end_exclusive": end, "batch": batch_number, "status": "success", "detail": "", "rows": len(frame)})
    return frames, logs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aliases", type=Path, default=Path("results/tables/phase7a_security_identity_aliases.csv"))
    parser.add_argument("--current-candidates", type=Path, default=Path("results/tables/phase2_candidate_universe.csv"))
    parser.add_argument("--existing-market", type=Path, default=Path("data/processed/prototype_market_panel.csv"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--tables-dir", type=Path, default=Path("results/tables"))
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args(); args.raw_dir.mkdir(parents=True, exist_ok=True); args.tables_dir.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(UTC).isoformat(); stamp = retrieved_at.replace(":", "").replace("+00:00", "Z")[:15]
    aliases = pd.read_csv(args.aliases)
    current = set(pd.read_csv(args.current_candidates)["yahoo_symbol"])
    all_tickers = sorted(set(aliases["yahoo_symbol"]))
    current_tickers = sorted(set(all_tickers) & current)
    historical_only = sorted(set(all_tickers) - current)

    frames1, logs1 = download_group(current_tickers, "2022-09-01", "2025-01-15", args.batch_size)
    frames2, logs2 = download_group(historical_only, "2022-09-01", "2025-05-29", args.batch_size)
    downloaded = pd.concat(frames1 + frames2, ignore_index=True) if frames1 or frames2 else pd.DataFrame(columns=["Date", *VALUE_COLUMNS, "yahoo_symbol"])
    raw_path = args.raw_dir / f"phase7a_yahoo_ohlcv_2022-09-01_2025-05-29_{stamp}.csv"
    downloaded.to_csv(raw_path, index=False)
    log = pd.DataFrame(logs1 + logs2)
    log.to_csv(args.tables_dir / "phase7a_yahoo_download_log.csv", index=False)

    existing = pd.read_csv(args.existing_market, parse_dates=["Date"])
    existing = existing.loc[existing["Date"].between("2025-01-15", "2025-05-28"), ["Date", *VALUE_COLUMNS, "yahoo_symbol"]].copy()
    existing["data_provenance"] = "reused_phase2_yahoo"
    downloaded["data_provenance"] = "phase7a_yahoo_download"
    combined = pd.concat([downloaded, existing], ignore_index=True, sort=False)
    combined = combined.sort_values(["yahoo_symbol", "Date", "data_provenance"]).drop_duplicates(["yahoo_symbol", "Date"], keep="first")
    combined.to_parquet(args.processed_dir / "phase7a_yahoo_alias_market.parquet", index=False)
    metadata = {
        "retrieved_at_utc": retrieved_at, "raw_filename": raw_path.name, "raw_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "requested_current_tickers_preexisting_overlap_reused": len(current_tickers), "requested_historical_only_tickers": len(historical_only),
        "successful_requests": int(log["status"].eq("success").sum()), "failed_requests": int((log["status"] != "success").sum()),
        "downloaded_rows": len(downloaded), "reused_rows": len(existing), "combined_rows": len(combined),
        "start": "2022-09-01", "historical_endpoint_end_exclusive": "2025-05-29", "auto_adjust": False, "actions": True,
    }
    (args.processed_dir / "phase7a_yahoo_acquisition_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
