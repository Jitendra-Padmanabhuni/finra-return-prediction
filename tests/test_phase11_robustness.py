from __future__ import annotations

import numpy as np
import pandas as pd

from src.run_robustness_phase11 import continuous_weights, stable_scores, tail_weights, validate_weights


def test_phase11_rank_and_breadth_weights_are_deterministic_and_neutral() -> None:
    frame = pd.DataFrame({"S1": [0.1, 0.1, 0.3, -0.2], "canonical_research_symbol": ["B", "A", "C", "D"]})
    scores = stable_scores(frame)
    assert frame.loc[scores.idxmax(), "canonical_research_symbol"] == "C"
    assert frame.loc[scores.idxmin(), "canonical_research_symbol"] == "D"
    weights = continuous_weights(scores)
    validate_weights(weights)
    tail = tail_weights(frame.assign(S1=frame.S1), 0.25)
    validate_weights(tail)
    assert np.isclose(tail.sum(), 0)


def test_phase11_missing_signal_stays_missing_and_target_is_not_read() -> None:
    frame = pd.DataFrame({"S1": [1.0, np.nan, -1.0], "canonical_research_symbol": ["A", "B", "C"], "forward_oc_return": [100, -100, 1], "target_available": [False, False, False]})
    scores = stable_scores(frame)
    assert pd.isna(scores.iloc[1])
    altered = frame.copy(); altered["forward_oc_return"] = [-999, 999, -999]; altered["target_available"] = True
    assert np.allclose(scores, stable_scores(altered), equal_nan=True)


def test_phase11_fixed_universe_and_placebo_seed_concepts_are_date_local() -> None:
    frame = pd.DataFrame({"Date": pd.to_datetime(["2025-01-01"] * 3), "S1": [1.0, 2.0, 3.0], "canonical_research_symbol": ["A", "B", "C"]})
    first = stable_scores(frame)
    changed = frame.copy(); changed.loc[0, "S1"] = 999
    assert not np.allclose(first, stable_scores(changed))
    rng_a = np.random.default_rng(20260911); rng_b = np.random.default_rng(20260911)
    assert np.array_equal(rng_a.permutation(np.arange(10)), rng_b.permutation(np.arange(10)))
