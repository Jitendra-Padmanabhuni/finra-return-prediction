"""Download immutable FINRA Regulation SHO daily files with a source manifest.

This utility performs acquisition only. It does not clean, aggregate, or model data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen


BASE_URL = "https://cdn.finra.org/equity/regsho/daily"
FILE_PREFIXES = {
    "consolidated_nms": "CNMSshvol",
    "nasdaq_chicago_trf": "FNQCshvol",
    "nasdaq_carteret_trf": "FNSQshvol",
    "nyse_trf": "FNYXshvol",
    "orf": "FORFshvol",
}


def download_file(facility: str, date: str, output_dir: Path) -> dict[str, str | int]:
    """Download one YYYYMMDD FINRA file without overwriting an existing file."""
    if facility not in FILE_PREFIXES:
        raise ValueError(f"Unknown facility {facility!r}; choose from {sorted(FILE_PREFIXES)}")
    if len(date) != 8 or not date.isdigit():
        raise ValueError("date must be YYYYMMDD")

    filename = f"{FILE_PREFIXES[facility]}{date}.txt"
    url = f"{BASE_URL}/{filename}"
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / filename
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite immutable raw file: {target}")

    with urlopen(url, timeout=60) as response:
        content = response.read()
    target.write_bytes(content)
    return {
        "facility": facility,
        "date": date,
        "filename": filename,
        "url": url,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facility", choices=sorted(FILE_PREFIXES), required=True)
    parser.add_argument("--date", required=True, help="Trade date as YYYYMMDD")
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    args = parser.parse_args()

    manifest_row = download_file(args.facility, args.date, args.output_dir)
    manifest = args.output_dir / "finra_source_manifest.jsonl"
    with manifest.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(manifest_row, sort_keys=True) + "\n")
    print(json.dumps(manifest_row, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

