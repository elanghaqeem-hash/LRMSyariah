"""Local, read-only demonstration of data quality status for WP1 synthetic files."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from lrm_data.schema import DatasetType
from lrm_data.validation import validate_batch


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate ONLY local synthetic sources")
    parser.add_argument("--input", type=Path, default=Path("examples/synthetic"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/wp1-dq-report.json"))
    args = parser.parse_args()
    expected_names = {f"{d.value}.xlsx" for d in DatasetType}
    supplied = {path.name: path.read_bytes() for path in args.input.glob("*.xlsx")}
    if set(supplied) != expected_names:
        raise SystemExit("Synthetic input file set is incomplete or unexpectedly extended")
    result = validate_batch(supplied, reporting_date=date(2026, 10, 30),
                            reporting_currency="IDR", required_datasets=list(DatasetType))
    output: dict[str, Any] = {
        "classification": "SYNTHETIC_TEST_ONLY_NOT_REGULATORY_REPORT",
        "summary": result.report.summary(),
        "findings": [dict(asdict(f), severity=f.severity.value) for f in result.report.findings],
        "input_hashes": {s.metadata.dataset_type.value: s.file_hash for s in result.sources},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True),
                           encoding="utf-8")
    print(json.dumps(output["summary"], indent=2))
    if result.report.status == "FAILED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
