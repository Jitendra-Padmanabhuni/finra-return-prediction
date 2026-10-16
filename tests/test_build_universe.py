from __future__ import annotations

import numpy as np
import pandas as pd

from src.build_universe import build_monthly_membership


def test_exact_20_date_median_differs_from_expanding_history() -> None:
    """Old observations must not change the March exact-20-date selection."""
    prior_dates = pd.bdate_range("2025-01-02", "2025-02-28")
    rebalance_date = pd.Timestamp("2025-03-03")
    dates = prior_dates.append(pd.DatetimeIndex([rebalance_date]))
    rows: list[dict[str, object]] = []
    last_twenty = set(prior_dates[-20:])
    for date in dates:
        rows.append({
            "source_symbol": "OLD",
            "Date": date,
            "Close": 1.0 if date in last_twenty else 1_000.0,
            "Volume": 1.0,
        })
        rows.append({
            "source_symbol": "RECENT",
            "Date": date,
            "Close": 10.0,
            "Volume": 1.0,
        })
    market = pd.DataFrame(rows)

    membership, audit = build_monthly_membership(market, candidate_count=1, liquidity_days=20)
    march = membership.loc[membership["rebalance_date"].eq(rebalance_date)]

    assert march["source_symbol"].tolist() == ["RECENT"]
    assert march["trailing_median_dollar_adv"].iloc[0] == 10.0
    assert march["trailing_observations"].iloc[0] == 20
    assert march["trailing_distinct_dates"].iloc[0] == 20
    assert march["screen_first_observation_date"].iloc[0] == prior_dates[-20]
    assert march["screen_last_observation_date"].iloc[0] == prior_dates[-1]

    expanding = (
        market.loc[market["Date"] < rebalance_date]
        .assign(dollar_volume=lambda frame: frame["Close"] * frame["Volume"])
        .groupby("source_symbol")["dollar_volume"]
        .median()
    )
    assert expanding.idxmax() == "OLD"
    march_audit = audit.loc[audit["rebalance_date"].eq("2025-03-03")].iloc[0]
    assert march_audit["window_shared_date_count"] == 20
    assert pd.Timestamp(march_audit["screen_last_observation_date"]) < rebalance_date


def test_requires_all_close_and_volume_observations() -> None:
    dates = pd.bdate_range("2025-01-02", periods=30)
    rows = []
    for symbol in ["COMPLETE", "MISSING"]:
        for date in dates:
            rows.append({"source_symbol": symbol, "Date": date, "Close": 10.0, "Volume": 100.0})
    market = pd.DataFrame(rows)
    market.loc[
        market["source_symbol"].eq("MISSING") & market["Date"].eq(dates[10]),
        "Close",
    ] = np.nan

    membership, _ = build_monthly_membership(market, candidate_count=2, liquidity_days=20)
    latest = membership.loc[membership["rebalance_date"].eq(membership["rebalance_date"].max())]
    assert "COMPLETE" in set(latest["source_symbol"])
    assert latest["trailing_observations"].eq(20).all()
