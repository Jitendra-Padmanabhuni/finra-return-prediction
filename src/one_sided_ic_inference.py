"""One-sided primary decision rule for Rank-IC and paired IC-difference tests.

Amendment approved 2026-09-12 (see `logs/research_log.md` and
`docs/one_sided_ic_inference_amendment_report.md`). Before this amendment, every
mean-IC and paired mean-IC-difference test in this project used a two-sided
primary standard: H0: mean IC = 0 vs HA: mean IC != 0, pass if |t| >= 2, with a
one-sided p-value (`stats.norm.sf(t)`) reported only as a supplementary,
non-decisive statistic.

This amendment switches those Rank-IC and paired IC-difference tests only to a
one-sided primary standard, reflecting a directional prior held before results
were examined (the signal, and any incremental difference between signals, is
expected to be positive if real):

    H0: mean IC <= 0          vs  HA: mean IC > 0
    H0: mean IC difference <= 0  vs  HA: mean IC difference > 0

using the standard one-sided 5% critical value under the normal approximation
this project already uses for its p-values, t >= 1.645, in place of the prior
two-sided t >= 2 bar.

Scope: standalone S0/S1/S2 mean Rank-IC tests and paired IC-difference tests
(S1-minus-S0, S2-minus-S1, S2-minus-S0) across Phases 5, 6 (regression
coefficients), 7, 7A, 7B, and 8 only.

Out of scope, unchanged and still two-sided as originally defined:
  - Phase 10 portfolio-return HAC tests (gross/net daily strategy returns).
  - The Phase 11 placebo/permutation test.
  - Decile-monotonicity diagnostics.
  - Any long-short / portfolio-return HAC test in any phase.
"""

from __future__ import annotations

ONE_SIDED_IC_CRITICAL_VALUE = 1.645
TWO_SIDED_IC_CRITICAL_VALUE_SUPERSEDED = 2.0


def ic_clears_one_sided_bar(hac_t: float, critical_value: float = ONE_SIDED_IC_CRITICAL_VALUE) -> bool:
    """Current primary decision rule for a Rank-IC or paired IC-difference test.

    H0: mean IC (or mean IC difference) <= 0
    HA: mean IC (or mean IC difference) > 0
    Passes if hac_t >= critical_value (default 1.645). Applies only to
    Rank-IC and paired IC-difference tests; portfolio-return, placebo, and
    decile-monotonicity tests are unaffected and use their own rules.
    """
    return bool(hac_t >= critical_value)


def ic_clears_two_sided_bar_superseded(hac_t: float, critical_value: float = TWO_SIDED_IC_CRITICAL_VALUE_SUPERSEDED) -> bool:
    """The prior primary rule for Rank-IC/paired-IC-difference tests (superseded 2026-09-12).

    Retained only so every historical verdict can be reproduced and compared
    against the current one-sided rule; it is no longer decisive for any
    Rank-IC or paired IC-difference test in this project.
    """
    return bool(abs(hac_t) >= critical_value)
