"""Fail-closed guard for WP0 unverified regulatory seed JSON.

This is NOT the WP2 active parameter governance system.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def validate_seed(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict) or not isinstance(data.get("regulatory_parameters"), list):
        return ["Regulatory seed must be an object with regulatory_parameters array"]
    entries = data["regulatory_parameters"]
    if not entries:
        errors.append("At least one placeholder parameter is required")
    seen: set[str] = set()
    for idx, item in enumerate(entries):
        label = f"parameter[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: must be object")
            continue
        pid = item.get("param_id")
        if not isinstance(pid, str) or not pid.strip() or pid in seen:
            errors.append(f"{label}: unique nonblank param_id required")
        else:
            seen.add(pid)
        if item.get("status") != "DRAFT_UNVERIFIED":
            errors.append(f"{label}: only DRAFT_UNVERIFIED allowed in WP0 seed")
        if item.get("value") is not None:
            errors.append(f"{label}: regulatory value MUST be null in WP0 seed")
        if item.get("effective_from") is not None:
            errors.append(f"{label}: effective_from MUST be null in WP0 seed")
        legal_basis = item.get("legal_basis")
        if not isinstance(legal_basis, str) or not legal_basis.strip():
            errors.append(f"{label}: legal_basis must be documented")
    return errors


def main() -> int:
    path = Path(__file__).resolve().parents[1] / "config" / "parameters.seed.json"
    data: Any = json.loads(path.read_text(encoding="utf-8"))
    issues = validate_seed(data)
    for issue in issues:
        print(f"FAIL: {issue}", file=sys.stderr)
    if issues:
        return 1
    print(f"PASS: {len(data['regulatory_parameters'])} unverified seeds; none are active")
    return 0


if __name__ == "__main__":
    sys.exit(main())
