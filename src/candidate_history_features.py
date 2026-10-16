"""Frozen Phase 6/7 features calculated on uninterrupted candidate histories."""

from __future__ import annotations

import numpy as np
import pandas as pd


VOLUME_WINDOW = 20
SIGNAL_WINDOW = 60
EPSILON = 0.000001


def median_absolute_deviation(values: np.ndarray) -> float:
    median = np.median(values)
    return float(np.median(np.abs(values - median)))


def add_candidate_history_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Add frozen features before any signal-date membership restriction.

    The input must contain one complete shared-date spine per candidate. The
    membership field is deliberately not used by any rolling calculation.
    """
    output = panel.sort_values(["canonical_research_symbol", "Date"]).copy()
    if output.duplicated(["Date", "canonical_research_symbol"]).any():
        raise ValueError("Candidate-history feature input has duplicate keys")
    output["ShortVolume_numeric"] = pd.to_numeric(output["ShortVolume"], errors="coerce")
    output["TotalVolume_numeric"] = pd.to_numeric(output["TotalVolume"], errors="coerce")
    valid_q = (
        output["finra_observation_present"]
        & output["ShortVolume_numeric"].notna()
        & output["TotalVolume_numeric"].gt(0)
    )
    output["q"] = np.where(valid_q, output["ShortVolume_numeric"] / output["TotalVolume_numeric"], np.nan)
    output["S0"] = -output["q"]

    valid_price = output["adjusted_open"].gt(0) & output["adjusted_close"].gt(0)
    output["same_day_oc_return"] = np.where(valid_price, output["adjusted_close"] / output["adjusted_open"] - 1, np.nan)
    output["reversal"] = -output["same_day_oc_return"]

    grouped = output.groupby("canonical_research_symbol", sort=False)
    output["prior_volume_median_20"] = grouped["Volume"].transform(
        lambda series: series.shift(1).rolling(VOLUME_WINDOW, min_periods=VOLUME_WINDOW).median()
    )
    valid_volume_surprise = output["Volume"].gt(0) & output["prior_volume_median_20"].gt(0)
    output["volume_surprise"] = np.nan
    output.loc[valid_volume_surprise, "volume_surprise"] = np.log(
        output.loc[valid_volume_surprise, "Volume"]
        / output.loc[valid_volume_surprise, "prior_volume_median_20"]
    )
    output["close_to_close_return"] = grouped["adjusted_close"].transform(lambda series: series / series.shift(1) - 1)
    output["realized_volatility"] = output.groupby("canonical_research_symbol", sort=False)["close_to_close_return"].transform(
        lambda series: series.shift(1).rolling(VOLUME_WINDOW, min_periods=VOLUME_WINDOW).std(ddof=1)
    )

    output["historical_median"] = grouped["q"].transform(
        lambda series: series.shift(1).rolling(SIGNAL_WINDOW, min_periods=SIGNAL_WINDOW).median()
    )
    output["historical_mad"] = grouped["q"].transform(
        lambda series: series.shift(1).rolling(SIGNAL_WINDOW, min_periods=SIGNAL_WINDOW).apply(
            median_absolute_deviation, raw=True
        )
    )
    output["prior_valid_q_count"] = grouped["q"].transform(
        lambda series: series.shift(1).rolling(SIGNAL_WINDOW, min_periods=SIGNAL_WINDOW).count()
    )
    output["exact_60_valid_history"] = output["prior_valid_q_count"].eq(SIGNAL_WINDOW)
    output["near_zero_mad"] = output["historical_mad"].le(EPSILON)
    output["z"] = np.where(
        output["q"].notna() & output["exact_60_valid_history"],
        (output["q"] - output["historical_median"]) / (1.4826 * output["historical_mad"] + EPSILON),
        np.nan,
    )
    output["S1"] = -output["z"]
    return output.sort_values(["Date", "canonical_research_symbol"]).reset_index(drop=True)
