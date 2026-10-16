"""Build the approved retrieval-date-stamped Yahoo Finance prototype universe.

This Phase 2 module acquires auxiliary OHLCV/actions data, reconciles source and
Yahoo symbols, and creates monthly membership using only prior trading days. It
does not read FINRA data, construct features, or calculate returns/signals.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from io import StringIO

import pandas as pd
import requests
import yfinance as yf


WIKIPEDIA_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
VALUE_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Splits"]
RAW_COLUMNS = ["Date", *VALUE_COLUMNS]


def yahoo_symbol(symbol: str) -> str:
    """Apply Yahoo's documented-style share-class convention to a source symbol."""
    return symbol.replace(".", "-")


def fetch_candidates(retrieved_at: str) -> pd.DataFrame:
    """Fetch current S&P 500 constituents as the approved fixed candidate source."""
    response = requests.get(
        WIKIPEDIA_SP500_URL,
        headers={"User-Agent": "finra-short-alpha-interview-poc/0.1 (research data audit)"},
        timeout=30,
    )
    response.raise_for_status()
    tables = pd.read_html(StringIO(response.text))
    table = next(table for table in tables if {"Symbol", "Security", "GICS Sector"}.issubset(table.columns))
    output = table[["Symbol", "Security", "GICS Sector", "GICS Sub-Industry", "Headquarters Location", "Date added", "CIK", "Founded"]].copy()
    output = output.rename(columns={"Symbol": "source_symbol", "Security": "security_name"})
    output["source_symbol"] = output["source_symbol"].astype(str).str.strip()
    output["yahoo_symbol"] = output["source_symbol"].map(yahoo_symbol)
    output["source_url"] = WIKIPEDIA_SP500_URL
    output["retrieved_at_utc"] = retrieved_at
    output["classification_basis"] = "current_sp500_constituent; no_known_etf_or_non_common_instrument_in_source_list"
    output["manual_exclusion_reason"] = pd.NA
    if output["source_symbol"].duplicated().any():
        raise ValueError("Candidate source returned duplicate symbols")
    return output


def download_market_data(candidates: pd.DataFrame, start: str, end: str, batch_size: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Download OHLCV/actions in batches and retain success/failure for every ticker."""
    success: list[pd.DataFrame] = []
    logs: list[dict[str, object]] = []
    ticker_to_source = dict(zip(candidates["yahoo_symbol"], candidates["source_symbol"], strict=True))
    tickers = candidates["yahoo_symbol"].tolist()
    for batch_number, offset in enumerate(range(0, len(tickers), batch_size), start=1):
        batch = tickers[offset : offset + batch_size]
        try:
            downloaded = yf.download(
                tickers=batch,
                start=start,
                end=end,
                auto_adjust=False,
                actions=True,
                group_by="column",
                progress=False,
                threads=True,
                timeout=30,
            )
        except Exception as exc:
            for ticker in batch:
                logs.append({"source_symbol": ticker_to_source[ticker], "yahoo_symbol": ticker, "batch": batch_number, "status": "download_exception", "detail": f"{type(exc).__name__}: {exc}", "rows": 0})
            continue
        for ticker in batch:
            try:
                frame = downloaded.xs(ticker, axis=1, level="Ticker", drop_level=True)
            except (KeyError, TypeError):
                logs.append({"source_symbol": ticker_to_source[ticker], "yahoo_symbol": ticker, "batch": batch_number, "status": "ticker_absent_from_response", "detail": "No column block returned", "rows": 0})
                continue
            frame = frame.dropna(how="all")
            if frame.empty:
                logs.append({"source_symbol": ticker_to_source[ticker], "yahoo_symbol": ticker, "batch": batch_number, "status": "no_rows", "detail": "No daily rows returned", "rows": 0})
                continue
            missing = [column for column in VALUE_COLUMNS if column not in frame.columns]
            if missing:
                logs.append({"source_symbol": ticker_to_source[ticker], "yahoo_symbol": ticker, "batch": batch_number, "status": "schema_failure", "detail": f"Missing columns: {missing}", "rows": len(frame)})
                continue
            frame = frame[VALUE_COLUMNS].copy()
            frame.index.name = "Date"
            frame = frame.reset_index()
            frame["Date"] = pd.to_datetime(frame["Date"]).dt.tz_localize(None)
            frame["source_symbol"] = ticker_to_source[ticker]
            frame["yahoo_symbol"] = ticker
            success.append(frame)
            logs.append({"source_symbol": ticker_to_source[ticker], "yahoo_symbol": ticker, "batch": batch_number, "status": "success", "detail": "", "rows": len(frame)})
    if not success:
        raise RuntimeError("Yahoo Finance returned no valid OHLCV data")
    return pd.concat(success, ignore_index=True), pd.DataFrame(logs)


def build_monthly_membership(market: pd.DataFrame, candidate_count: int, liquidity_days: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply a monthly top-N dollar-ADV screen using strictly prior observations."""
    panel = market.copy()
    panel["dollar_volume"] = panel["Close"] * panel["Volume"]
    panel = panel.sort_values(["source_symbol", "Date"])
    records: list[pd.DataFrame] = []
    audit: list[dict[str, object]] = []
    trade_dates = panel["Date"].drop_duplicates().sort_values().reset_index(drop=True)
    month_starts = trade_dates.groupby(trade_dates.dt.to_period("M")).min()
    for _, rebalance_date in month_starts.items():
        history = panel.loc[panel["Date"] < rebalance_date, ["source_symbol", "Date", "dollar_volume"]]
        last_history_date = history["Date"].max() if not history.empty else pd.NaT
        trailing = history.groupby("source_symbol", as_index=False)["dollar_volume"].agg(
            trailing_observations="count", trailing_median_dollar_adv="median"
        )
        eligible = trailing.loc[trailing["trailing_observations"] >= liquidity_days].copy()
        eligible = eligible.sort_values(["trailing_median_dollar_adv", "source_symbol"], ascending=[False, True]).head(candidate_count)
        eligible["rebalance_date"] = rebalance_date
        eligible["universe_member"] = True
        eligible["screen_last_observation_date"] = last_history_date
        eligible["screen_uses_only_dates_before_rebalance"] = True
        records.append(eligible)
        audit.append({
            "rebalance_date": rebalance_date.date().isoformat(),
            "eligible_with_history": len(trailing.loc[trailing["trailing_observations"] >= liquidity_days]),
            "selected_members": len(eligible),
            "liquidity_days": liquidity_days,
        })
    return pd.concat(records, ignore_index=True), pd.DataFrame(audit)


def prepare_market_panel(market: pd.DataFrame) -> pd.DataFrame:
    """Create a clean Yahoo-only market panel while retaining raw and action fields."""
    panel = market.copy()
    if panel.duplicated(["source_symbol", "Date"]).any():
        raise ValueError("Duplicate Yahoo source_symbol/date observations")
    factor = panel["Adj Close"] / panel["Close"]
    if (panel["Close"] <= 0).any():
        raise ValueError("Nonpositive close prevents adjusted-OHLC construction")
    panel["adjustment_factor"] = factor
    panel["adjusted_open"] = panel["Open"] * factor
    panel["adjusted_high"] = panel["High"] * factor
    panel["adjusted_low"] = panel["Low"] * factor
    panel["adjusted_close"] = panel["Adj Close"]
    panel["dollar_volume"] = panel["Close"] * panel["Volume"]
    return panel.sort_values(["source_symbol", "Date"]).reset_index(drop=True)


def expand_daily_membership(market: pd.DataFrame, membership: pd.DataFrame) -> pd.DataFrame:
    """Hold each monthly selection fixed until the next monthly refresh."""
    dates = market[["Date"]].drop_duplicates().sort_values("Date")
    rebalances = membership[["rebalance_date"]].drop_duplicates().sort_values("rebalance_date")
    date_map = pd.merge_asof(
        dates, rebalances, left_on="Date", right_on="rebalance_date", direction="backward"
    ).dropna(subset=["rebalance_date"])
    daily = date_map.merge(membership, on="rebalance_date", how="inner")
    daily = daily.rename(columns={"rebalance_date": "universe_refresh_date"})
    daily["universe_member"] = True
    return daily.sort_values(["Date", "source_symbol"]).reset_index(drop=True)


def missing_market_dates(market: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    """List every candidate/date absent from Yahoo's returned trading-date panel."""
    dates = market[["Date"]].drop_duplicates().sort_values("Date")
    symbols = candidates[["source_symbol", "yahoo_symbol"]].drop_duplicates().sort_values("source_symbol")
    expected = symbols.merge(dates, how="cross")
    observed = market[["source_symbol", "Date"]].drop_duplicates()
    output = expected.merge(observed, on=["source_symbol", "Date"], how="left", indicator=True)
    output = output.loc[output["_merge"] == "left_only"].drop(columns="_merge")
    output["status"] = "missing_market_date"
    return output.sort_values(["source_symbol", "Date"]).reset_index(drop=True)


def inspect_actions_and_returns(market: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retain split dates and report extreme same-series daily close returns for Phase 2 review."""
    panel = market.sort_values(["source_symbol", "Date"]).copy()
    panel["close_return"] = panel.groupby("source_symbol")["Close"].pct_change(fill_method=None)
    splits = panel.loc[panel["Stock Splits"].fillna(0) != 0, ["source_symbol", "yahoo_symbol", "Date", "Stock Splits"]].copy()
    extremes = panel.loc[panel["close_return"].abs() >= 0.25, ["source_symbol", "yahoo_symbol", "Date", "Close", "Adj Close", "close_return", "Stock Splits"]].copy()
    return splits, extremes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2025-01-15")
    parser.add_argument("--end", default="2026-09-01", help="Exclusive end date")
    parser.add_argument("--candidate-count", type=int, default=400)
    parser.add_argument("--liquidity-days", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--tables-dir", type=Path, default=Path("results/tables"))
    args = parser.parse_args()
    retrieved_at = datetime.now(UTC).isoformat()
    stamp = retrieved_at.replace(":", "").replace("+00:00", "Z")[:15]
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    args.processed_dir.mkdir(parents=True, exist_ok=True)
    args.tables_dir.mkdir(parents=True, exist_ok=True)

    candidates = fetch_candidates(retrieved_at)
    candidates.to_csv(args.raw_dir / f"sp500_candidates_{stamp}.csv", index=False)
    market, download_log = download_market_data(candidates, args.start, args.end, args.batch_size)
    market.to_csv(args.raw_dir / f"yahoo_ohlcv_{args.start}_{args.end}_{stamp}.csv", index=False)
    download_log.to_csv(args.tables_dir / "phase2_market_download_log.csv", index=False)
    market_panel = prepare_market_panel(market)
    membership, membership_audit = build_monthly_membership(market_panel, args.candidate_count, args.liquidity_days)
    daily_membership = expand_daily_membership(market_panel, membership)
    missing_dates = missing_market_dates(market_panel, candidates)
    splits, extremes = inspect_actions_and_returns(market_panel)

    candidates.to_csv(args.tables_dir / "phase2_candidate_universe.csv", index=False)
    candidates[["source_symbol", "yahoo_symbol"]].assign(
        transformed=lambda frame: frame["source_symbol"] != frame["yahoo_symbol"]
    ).to_csv(args.tables_dir / "phase2_symbol_reconciliation.csv", index=False)
    market_panel.to_csv(args.processed_dir / "prototype_market_panel.csv", index=False)
    membership.to_csv(args.processed_dir / "prototype_universe_monthly.csv", index=False)
    daily_membership.to_csv(args.processed_dir / "prototype_universe_daily.csv", index=False)
    membership_audit.to_csv(args.tables_dir / "phase2_universe_coverage.csv", index=False)
    missing_dates.to_csv(args.tables_dir / "phase2_missing_market_dates.csv", index=False)
    splits.to_csv(args.tables_dir / "phase2_split_events.csv", index=False)
    extremes.to_csv(args.tables_dir / "phase2_extreme_close_returns.csv", index=False)

    metadata = {
        "retrieved_at_utc": retrieved_at,
        "candidate_source": WIKIPEDIA_SP500_URL,
        "candidate_count": len(candidates),
        "market_start": args.start,
        "market_end_exclusive": args.end,
        "monthly_selected_count": args.candidate_count,
        "liquidity_lookback_days": args.liquidity_days,
        "successful_downloads": int((download_log["status"] == "success").sum()),
        "failed_downloads": int((download_log["status"] != "success").sum()),
        "market_rows": len(market),
        "missing_market_dates": len(missing_dates),
        "split_events": len(splits),
        "extreme_close_returns": len(extremes),
    }
    (args.processed_dir / "phase2_market_universe_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
