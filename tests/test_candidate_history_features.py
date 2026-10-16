from __future__ import annotations

import numpy as np
import pandas as pd

from src.candidate_history_features import add_candidate_history_features


def test_membership_interruption_does_not_interrupt_candidate_history() -> None:
    dates = pd.bdate_range("2025-01-02", periods=90)
    panel = pd.DataFrame({
        "Date": dates,
        "canonical_research_symbol": "REENTER",
        "ShortVolume": np.linspace(40, 70, len(dates)),
        "TotalVolume": 100.0,
        "finra_observation_present": True,
        "adjusted_open": 100.0 + np.arange(len(dates)),
        "adjusted_close": 101.0 + np.arange(len(dates)),
        "Volume": 1_000_000.0 + np.arange(len(dates)),
        "universe_member": True,
    })
    panel.loc[panel.index[65:75], "universe_member"] = False
    featured = add_candidate_history_features(panel)

    reentry = featured.iloc[75]
    assert reentry["universe_member"]
    assert reentry["prior_valid_q_count"] == 60
    assert reentry["S1"] == reentry["S1"]  # not NaN
    assert reentry["volume_surprise"] == reentry["volume_surprise"]
    assert reentry["realized_volatility"] == reentry["realized_volatility"]

    changed_future = panel.copy()
    changed_future.loc[changed_future.index > 75, "ShortVolume"] = 1.0
    featured_changed = add_candidate_history_features(changed_future)
    for column in ["historical_median", "historical_mad", "S1", "volume_surprise", "realized_volatility"]:
        assert np.isclose(featured.loc[75, column], featured_changed.loc[75, column], equal_nan=True)
