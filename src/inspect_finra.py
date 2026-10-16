"""Audit raw FINRA Regulation SHO daily files; no cleaning or feature creation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


EXPECTED_HEADER = ["Date", "Symbol", "ShortVolume", "ShortExemptVolume", "TotalVolume", "Market"]
VOLUME_FIELDS = ("ShortVolume", "ShortExemptVolume", "TotalVolume")
PREFIX_TO_FACILITY = {
    "CNMSshvol": "consolidated_nms",
    "FNQCshvol": "nasdaq_chicago_trf_chicago",
    "FNSQshvol": "nasdaq_carteret_trf",
    "FNYXshvol": "nyse_trf",
    "FORFshvol": "orf",
}


def facility_from_name(path: Path) -> str:
    for prefix, facility in PREFIX_TO_FACILITY.items():
        if path.name.startswith(prefix):
            return facility
    return "unknown"


def parse_decimal(value: str, field: str, path: Path, line_number: int) -> Decimal:
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{path}:{line_number}: invalid {field} value {value!r}") from exc
    if not result.is_finite():
        raise ValueError(f"{path}:{line_number}: non-finite {field} value {value!r}")
    return result


def read_finra_file(path: Path) -> tuple[list[dict[str, str]], dict[str, object]]:
    """Read a raw file, validating its header and numeric record-count trailer."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        raise ValueError(f"{path}: expected header and trailer")
    header = lines[0].split("|")
    if header != EXPECTED_HEADER:
        raise ValueError(f"{path}: unexpected header {header!r}")
    try:
        trailer_count = int(lines[-1])
    except ValueError as exc:
        raise ValueError(f"{path}: trailer is not an integer record count: {lines[-1]!r}") from exc

    records = list(csv.DictReader(lines[1:-1], fieldnames=EXPECTED_HEADER, delimiter="|"))
    if len(records) != trailer_count:
        raise ValueError(f"{path}: {len(records)} rows but trailer reports {trailer_count}")
    return records, {
        "file": path.name,
        "facility": facility_from_name(path),
        "row_count": len(records),
        "trailer_count": trailer_count,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def decimal_summary(values: list[Decimal]) -> dict[str, str | None]:
    if not values:
        return {"min": None, "max": None}
    return {"min": str(min(values)), "max": str(max(values))}


def audit_file(path: Path) -> tuple[list[dict[str, str]], dict[str, object]]:
    records, report = read_finra_file(path)
    missing = Counter()
    numeric = {field: [] for field in VOLUME_FIELDS}
    dates: set[str] = set()
    symbols: set[str] = set()
    markets: Counter[str] = Counter()
    keys: list[tuple[str, str, str]] = []
    fractional = Counter()
    zero_total = 0
    nonpositive_total = 0
    inequality_violations = 0

    for index, row in enumerate(records, start=2):
        for field, value in row.items():
            if value == "":
                missing[field] += 1
        dates.add(row["Date"])
        symbols.add(row["Symbol"])
        markets[row["Market"]] += 1
        keys.append((row["Date"], row["Symbol"], row["Market"]))
        parsed = {field: parse_decimal(row[field], field, path, index) for field in VOLUME_FIELDS}
        for field, value in parsed.items():
            numeric[field].append(value)
            if value != value.to_integral_value():
                fractional[field] += 1
        if parsed["TotalVolume"] == 0:
            zero_total += 1
        if parsed["TotalVolume"] <= 0:
            nonpositive_total += 1
        if parsed["ShortVolume"] > parsed["TotalVolume"]:
            inequality_violations += 1

    duplicate_rows = len(keys) - len(set(keys))
    ratios = [
        parse_decimal(row["ShortVolume"], "ShortVolume", path, n)
        / parse_decimal(row["TotalVolume"], "TotalVolume", path, n)
        for n, row in enumerate(records, start=2)
        if parse_decimal(row["TotalVolume"], "TotalVolume", path, n) > 0
    ]
    ratios_sorted = sorted(ratios)

    def quantile(probability: Decimal) -> str | None:
        if not ratios_sorted:
            return None
        position = int((len(ratios_sorted) - 1) * float(probability))
        return str(ratios_sorted[position])

    report.update(
        {
            "trade_dates": sorted(dates),
            "unique_symbols": len(symbols),
            "market_values": dict(sorted(markets.items())),
            "missing_by_field": dict(sorted(missing.items())),
            "duplicate_date_symbol_market_rows": duplicate_rows,
            "zero_total_volume_rows": zero_total,
            "nonpositive_total_volume_rows": nonpositive_total,
            "short_volume_greater_than_total_volume_rows": inequality_violations,
            "fractional_value_rows": dict(fractional),
            "volume_ranges": {field: decimal_summary(values) for field, values in numeric.items()},
            "short_volume_ratio_quantiles": {
                "min": quantile(Decimal("0")),
                "p01": quantile(Decimal("0.01")),
                "p50": quantile(Decimal("0.50")),
                "p99": quantile(Decimal("0.99")),
                "max": quantile(Decimal("1")),
            },
        }
    )
    return records, report


def compare_consolidated(raw_dir: Path, date: str) -> dict[str, object] | None:
    consolidated = raw_dir / f"CNMSshvol{date}.txt"
    components = [raw_dir / f"{prefix}{date}.txt" for prefix in ("FNQCshvol", "FNSQshvol", "FNYXshvol")]
    if not consolidated.exists() or not all(path.exists() for path in components):
        return None
    consolidated_rows, _ = read_finra_file(consolidated)
    component_rows = [row for path in components for row in read_finra_file(path)[0]]

    def aggregate(rows: list[dict[str, str]]) -> dict[str, dict[str, Decimal]]:
        output: dict[str, dict[str, Decimal]] = {}
        for row in rows:
            bucket = output.setdefault(row["Symbol"], {field: Decimal("0") for field in VOLUME_FIELDS})
            for field in VOLUME_FIELDS:
                bucket[field] += parse_decimal(row[field], field, Path("reconciliation"), 0)
        return output

    combined = aggregate(component_rows)
    reported = aggregate(consolidated_rows)
    common = sorted(set(combined) & set(reported))
    missing_in_consolidated = sorted(set(combined) - set(reported))
    missing_in_components = sorted(set(reported) - set(combined))
    mismatches = []
    for symbol in common:
        deltas = {field: combined[symbol][field] - reported[symbol][field] for field in VOLUME_FIELDS}
        if any(delta != 0 for delta in deltas.values()):
            mismatches.append({"symbol": symbol, "deltas": {field: str(value) for field, value in deltas.items()}})
    return {
        "date": date,
        "component_files": [path.name for path in components],
        "consolidated_file": consolidated.name,
        "common_symbols": len(common),
        "missing_in_consolidated_count": len(missing_in_consolidated),
        "missing_in_components_count": len(missing_in_components),
        "mismatch_count": len(mismatches),
        "mismatch_examples": mismatches[:10],
    }


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--tables-dir", type=Path, default=Path("results/tables"))
    parser.add_argument("--report-path", type=Path, default=Path("results/phase1_finra_quality_report.json"))
    args = parser.parse_args()
    files = sorted(args.raw_dir.glob("*shvol*.txt"))
    if not files:
        raise FileNotFoundError(f"No FINRA daily files found in {args.raw_dir}")
    args.tables_dir.mkdir(parents=True, exist_ok=True)
    args.report_path.parent.mkdir(parents=True, exist_ok=True)

    all_records: list[dict[str, str]] = []
    file_reports = []
    for path in files:
        records, report = audit_file(path)
        all_records.extend([{**row, "SourceFile": path.name} for row in records])
        file_reports.append(report)
    dates = sorted({date for report in file_reports for date in report["trade_dates"]})
    reconciliation = [item for date in dates if (item := compare_consolidated(args.raw_dir, date))]

    report = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "purpose": "Phase 1 raw-data audit only; no cleaning, aggregation, universe filter, or alpha computation.",
        "expected_header": EXPECTED_HEADER,
        "files": file_reports,
        "consolidated_component_reconciliation": reconciliation,
    }
    args.report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    coverage_rows = [
        {
            "file": item["file"],
            "facility": item["facility"],
            "trade_dates": ";".join(item["trade_dates"]),
            "rows": item["row_count"],
            "unique_symbols": item["unique_symbols"],
            "zero_total_volume_rows": item["zero_total_volume_rows"],
            "duplicate_date_symbol_market_rows": item["duplicate_date_symbol_market_rows"],
        }
        for item in file_reports
    ]
    write_csv(args.tables_dir / "phase1_coverage_summary.csv", coverage_rows, list(coverage_rows[0]))
    example_rows = all_records[:10]
    write_csv(args.tables_dir / "phase1_example_rows.csv", example_rows, list(example_rows[0]))
    print(f"Audited {len(files)} files and wrote {args.report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

