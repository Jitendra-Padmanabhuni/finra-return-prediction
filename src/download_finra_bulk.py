"""Download immutable FINRA Consolidated NMS files for a supplied trading calendar."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests


BASE_URL = "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{date}.txt"
HEADER = "Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market"


def validate(content: bytes) -> int:
    lines = content.decode("utf-8").splitlines()
    if len(lines) < 2 or lines[0] != HEADER:
        raise ValueError("unexpected FINRA header or missing trailer")
    trailer = int(lines[-1])
    if len(lines) - 2 != trailer:
        raise ValueError(f"trailer={trailer}; data_rows={len(lines)-2}")
    return trailer


def acquire(date: pd.Timestamp, raw_dir: Path) -> dict[str, object]:
    trade_date = date.strftime("%Y%m%d")
    filename = f"CNMSshvol{trade_date}.txt"
    target = raw_dir / filename
    url = BASE_URL.format(date=trade_date)
    retrieved_at = datetime.now(UTC).isoformat()
    try:
        if target.exists():
            content = target.read_bytes()
            status = "preexisting_verified"
        else:
            response = requests.get(url, headers={"User-Agent": "finra-short-alpha-interview-poc/0.1"}, timeout=90)
            response.raise_for_status()
            content = response.content
            temporary = target.with_suffix(".txt.partial")
            temporary.write_bytes(content)
            os.replace(temporary, target)
            status = "downloaded"
        return {
            "trade_date": trade_date, "filename": filename, "url": url,
            "retrieved_at_utc": retrieved_at, "status": status,
            "sha256": hashlib.sha256(content).hexdigest(), "trailer_count": validate(content),
            "revision_status": "undetermined_current_endpoint_no_version_metadata",
            "error": "",
        }
    except Exception as exc:
        return {"trade_date": trade_date, "filename": filename, "url": url, "retrieved_at_utc": retrieved_at,
                "status": "failed", "sha256": "", "trailer_count": None,
                "revision_status": "undetermined", "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dates-csv", required=True, type=Path)
    parser.add_argument("--raw-dir", default=Path("data/raw"), type=Path)
    parser.add_argument("--manifest", default=Path("data/raw/finra_consolidated_nms_manifest.jsonl"), type=Path)
    parser.add_argument("--log", default=Path("results/tables/phase3_finra_download_log.csv"), type=Path)
    args = parser.parse_args()
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    dates = pd.read_csv(args.dates_csv, parse_dates=["Date"])["Date"].drop_duplicates().sort_values().tolist()
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        rows = list(executor.map(lambda date: acquire(date, args.raw_dir), dates))
    rows = sorted(rows, key=lambda row: row["trade_date"])
    args.log.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.log, index=False)
    with args.manifest.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    failed = sum(row["status"] == "failed" for row in rows)
    print(f"FINRA files={len(rows)}; failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

