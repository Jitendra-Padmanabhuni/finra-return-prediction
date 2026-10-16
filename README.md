# FINRA Short-Sale Volume Alpha Research

Research pipeline for engineering cross-sectional features from FINRA daily short-sale volume and forecasting next-session open-to-close returns among liquid U.S. equities.

## Overview

The project tests whether unusually high short-sale volume contains information about relative stock returns on the following trading day. It combines FINRA Consolidated NMS short-volume files with daily OHLCV data, applies strictly lagged feature construction, and evaluates signals using cross-sectional rank correlation and dollar-neutral long-short portfolios.

FINRA short volume measures trades marked short and reported through FINRA facilities. It is distinct from total market volume and outstanding short interest.

## Feature engineering

Three signal representations are evaluated:

- **Raw short-volume signal (`S0`)**: negative short-volume ratio, where lower short activity receives a higher score.
- **Stock-relative abnormality (`S1`)**: the current ratio normalized against the stock's previous 60 observations using a robust median/MAD transformation.
- **Conditioned abnormality (`S2`)**: `S1` residualized within daily volume-surprise and prior-volatility groups to reduce exposure to contemporaneous trading conditions.

Signals are converted into bounded daily cross-sectional ranks from -1 to +1. Features use only information available by the end of day `t`; the prediction target is the adjusted open-to-close return on the next shared trading session.

## Evaluation design

- Monthly universe of 400 liquid U.S. equities selected using the preceding 20 trading days
- 918 evaluation dates across two separately analyzed samples
- Next-session adjusted open-to-close return target
- HAC standard errors for serially dependent daily statistics
- Gross, dollar-neutral long-short portfolio evaluation
- Robustness checks covering liquidity neutrality, fixed universes, time stability, outliers, concentration, and score permutations

## Results

The conditioned signal (`S2`) produced positive rank predictiveness and gross long-short performance in both evaluation samples:

| Evaluation period | Mean Rank IC | HAC(5) t-statistic | Gross long-short Sharpe |
| --- | ---: | ---: | ---: |
| 2023-01-03 to 2025-05-27 | 0.00832 | 3.48 | 1.61 |
| 2025-05-28 to 2026-08-31 | 0.01178 | 2.55 | 1.42 |

In the recent sample, the continuous dollar-neutral strategy generated a gross market-model alpha of 1.56 basis points per day with a HAC(5) t-statistic of 1.71 and near-zero market beta. The signal remained positive in leave-one-year-out tests and under fixed-universe and liquidity-neutral constructions.

All portfolio results above are gross and frictionless unless otherwise stated.

## Repository contents

```text
config/       Research configuration and signal definitions
docs/         Methodology and empirical reports
scripts/      Environment and data-coverage utilities
src/          Data preparation, feature engineering, evaluation, and backtests
tests/        Automated validation and regression tests
```

Large raw and processed datasets are excluded from version control.

## Setup

The project supports Python 3.11-3.13.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/check_environment.py
```

Run the test suite with:

```bash
pytest -q
```
