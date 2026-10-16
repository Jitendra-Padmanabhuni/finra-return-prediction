"""Probe FINRA Consolidated NMS endpoint availability for a preselected date set."""

from __future__ import annotations

import argparse
import concurrent.futures
from pathlib import Path

import pandas as pd
import requests


BASE_URL = "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{date}.txt"


def probe(date: pd.Timestamp) -> dict[str, str | int]:
    url = BASE_URL.format(date=date.strftime("%Y%m%d"))
    try:
        response = requests.head(url, timeout=20, allow_redirects=True)
        return {"trade_date": date.date().isoformat(), "url": url, "status_code": response.status_code, "available": int(response.status_code == 200)}
    except requests.RequestException as exc:
        return {"trade_date": date.date().isoformat(), "url": url, "status_code": -1, "available": 0, "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dates-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("results/tables/phase2_finra_availability.csv"))
    args = parser.parse_args()
    dates = pd.read_csv(args.dates_csv, parse_dates=["Date"])["Date"].drop_duplicates().sort_values()
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        rows = list(executor.map(probe, dates))
    result = pd.DataFrame(rows).sort_values("trade_date")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    unavailable = int((result["available"] == 0).sum())
    print(f"Probed {len(result)} dates; unavailable={unavailable}")
    return 1 if unavailable else 0


if __name__ == "__main__":
    raise SystemExit(main())

