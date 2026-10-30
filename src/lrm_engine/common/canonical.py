"""Deterministic, float-free canonical JSON & hashes; rule: ENG-TRACE-001.

Legal basis: calculation auditability engineering control; not a calculation rule.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from lrm_engine.common.decimal_math import decimal_plain


def _normalize(value: Any) -> Any:
    if isinstance(value, float):
        raise TypeError("floats are forbidden in canonical calculations")
    if isinstance(value, Decimal):
        return decimal_plain(value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("naive timestamps are forbidden")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return _normalize(value.value)
    if is_dataclass(value) and not isinstance(value, type):
        return _normalize(asdict(value))
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise TypeError("canonical mapping keys must be strings")
        return {k: _normalize(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    raise TypeError(f"unsupported canonical type: {type(value).__name__}")


def canonical_json(value: Any) -> bytes:
    """Serialize without locale settings, whitespace or non-finite numerics."""
    return json.dumps(
        _normalize(value), sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def sha256_canonical(value: Any) -> str:
    """SHA-256 of canonical UTF-8 JSON payload."""
    return hashlib.sha256(canonical_json(value)).hexdigest()
