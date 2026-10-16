from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_corrected_monthly_and_daily_universe_invariants() -> None:
    market = pd.read_csv(ROOT / "data/processed/prototype_market_panel.csv", parse_dates=["Date"])
    monthly = pd.read_csv(ROOT / "data/processed/prototype_universe_monthly.csv", parse_dates=[
        "rebalance_date", "screen_first_observation_date", "screen_last_observation_date"
    ])
    daily = pd.read_csv(ROOT / "data/processed/prototype_universe_daily.csv", parse_dates=["Date", "universe_refresh_date"])
    dates = market["Date"].drop_duplicates().sort_values().reset_index(drop=True)

    assert not monthly.duplicated(["rebalance_date", "source_symbol"]).any()
    assert monthly.groupby("rebalance_date").size().eq(400).all()
    assert monthly["trailing_observations"].eq(20).all()
    assert monthly["trailing_distinct_dates"].eq(20).all()
    assert monthly["liquidity_window_shared_date_count"].eq(20).all()
    assert (monthly["screen_last_observation_date"] < monthly["rebalance_date"]).all()
    for rebalance, group in monthly.groupby("rebalance_date"):
        location = int(dates.searchsorted(rebalance))
        assert group["screen_first_observation_date"].eq(dates.iloc[location - 20]).all()
        assert group["screen_last_observation_date"].eq(dates.iloc[location - 1]).all()
        window_dates = dates.iloc[location - 20 : location]
        recomputed = (
            market.loc[market["Date"].isin(window_dates)]
            .assign(recomputed_dollar_volume=lambda frame: frame["Close"] * frame["Volume"])
            .groupby("source_symbol", as_index=False)["recomputed_dollar_volume"]
            .median()
        )
        selected = group.merge(recomputed, on="source_symbol", how="left", validate="one_to_one")
        assert np.allclose(
            selected["trailing_median_dollar_adv"],
            selected["recomputed_dollar_volume"],
            rtol=0,
            atol=1e-5,
        )

    assert not daily.duplicated(["Date", "source_symbol"]).any()
    assert daily.groupby("Date").size().eq(400).all()
    expected_refresh = pd.merge_asof(
        daily[["Date"]].drop_duplicates().sort_values("Date"),
        monthly[["rebalance_date"]].drop_duplicates().sort_values("rebalance_date"),
        left_on="Date", right_on="rebalance_date", direction="backward",
    )
    observed_refresh = daily[["Date", "universe_refresh_date"]].drop_duplicates().sort_values("Date")
    assert observed_refresh["universe_refresh_date"].reset_index(drop=True).equals(
        expected_refresh["rebalance_date"].reset_index(drop=True)
    )


def test_master_target_and_signal_invariants() -> None:
    daily = pd.read_csv(ROOT / "data/processed/prototype_universe_daily.csv", parse_dates=["Date"])
    master = pd.read_parquet(ROOT / "data/processed/master_stock_day_panel.parquet")
    target = pd.read_parquet(ROOT / "data/processed/master_stock_day_with_target.parquet")
    phase7 = pd.read_parquet(ROOT / "data/processed/phase7_abnormal_signal_panel.parquet")

    assert len(master) == len(daily) == 150_800
    assert not master.duplicated(["Date", "canonical_research_symbol"]).any()
    missing_finra = ~master["finra_observation_present"]
    assert master.loc[missing_finra, ["ShortVolume", "ShortExemptVolume", "TotalVolume"]].isna().all().all()
    assert not target.duplicated(["Date", "canonical_research_symbol"]).any()
    available = target["target_available"]
    assert (target.loc[available, "designated_target_date"] > target.loc[available, "Date"]).all()
    calendar = pd.Series(pd.to_datetime(target["Date"].unique())).sort_values().reset_index(drop=True)
    extension_date = pd.Timestamp("2026-09-01")
    calendar = pd.concat([calendar, pd.Series([extension_date])]).drop_duplicates().sort_values().reset_index(drop=True)
    mapping = dict(zip(calendar.iloc[:-1], calendar.iloc[1:], strict=True))
    assert target.loc[target["designated_target_date"].notna()].apply(
        lambda row: row["designated_target_date"] == mapping[row["Date"]], axis=1
    ).all()

    q = phase7["q"].dropna()
    assert q.between(-1e-12, 1 + 1e-12).all()
    eligible = phase7["s1_eligible"]
    assert phase7.loc[eligible, "prior_valid_q_count"].eq(60).all()
    assert phase7.loc[eligible, "prior_present_count"].eq(60).all()
    assert np.isfinite(phase7.loc[eligible, "S1"]).all()
    assert phase7.loc[eligible, "Date"].nunique() == 317


def test_preserved_inputs_match_legacy_archive() -> None:
    current_candidates = pd.read_csv(ROOT / "results/tables/phase2_candidate_universe.csv")
    legacy_candidates = pd.read_csv(ROOT / "legacy/expanding_liquidity_window/results_tables/phase2_candidate_universe.csv")
    current_market = pd.read_csv(ROOT / "data/processed/prototype_market_panel.csv")
    legacy_market = pd.read_csv(ROOT / "legacy/expanding_liquidity_window/data_processed/prototype_market_panel.csv")
    pd.testing.assert_frame_equal(current_candidates, legacy_candidates)
    pd.testing.assert_frame_equal(current_market, legacy_market)


def test_candidate_history_panel_preserves_full_spine_and_membership_gate() -> None:
    candidates = pd.read_csv(ROOT / "results/tables/phase2_candidate_universe.csv")
    market = pd.read_csv(ROOT / "data/processed/prototype_market_panel.csv", parse_dates=["Date"])
    history = pd.read_parquet(ROOT / "data/processed/candidate_history_panel.parquet")
    members = pd.read_csv(ROOT / "data/processed/prototype_universe_daily.csv", parse_dates=["Date"])
    assert len(history) == history["Date"].nunique() * len(candidates) == 205_224
    assert not history.duplicated(["Date", "canonical_research_symbol"]).any()
    assert history.groupby("Date").size().eq(len(candidates)).all()
    expected = members[["Date", "source_symbol"]].rename(columns={"source_symbol": "canonical_research_symbol"})
    actual = history.loc[history["universe_member"], ["Date", "canonical_research_symbol"]]
    pd.testing.assert_frame_equal(
        actual.sort_values(list(actual.columns)).reset_index(drop=True),
        expected.sort_values(list(expected.columns)).reset_index(drop=True),
    )
    assert history["market_availability_status"].isin(["present", "missing_market_observation"]).all()
    assert history["finra_availability_status"].isin(["present", "missing_finra_observation"]).all()
