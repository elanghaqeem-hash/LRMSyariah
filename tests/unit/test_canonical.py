from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum

import pytest

from lrm_engine.common.canonical import canonical_json, sha256_canonical


class Status(Enum):
    READY = "READY"


@dataclass(frozen=True)
class Example:
    amount: Decimal
    status: Status


@pytest.mark.unit
def test_canonical_equivalent_mappings():
    a = {"b": Decimal("1.00"), "a": [Decimal("1E+3"), 1]}
    b = {"a": (Decimal("1000"), 1), "b": Decimal("1")}
    assert canonical_json(a) == canonical_json(b)
    assert sha256_canonical(a) == sha256_canonical(b)
    assert len(sha256_canonical(a)) == 64


@pytest.mark.unit
def test_timestamps_dates_enums_dataclasses():
    in_jakarta = datetime(2026, 10, 30, 7, 0, tzinfo=timezone(timedelta(hours=7)))
    in_utc = datetime(2026, 10, 30, 0, 0, tzinfo=timezone.utc)
    assert canonical_json(in_jakarta) == canonical_json(in_utc)
    assert canonical_json(date(2026, 10, 30)) == b'"2026-10-30"'
    assert canonical_json(Example(Decimal("2.0"), Status.READY)) == (
        b'{"amount":"2","status":"READY"}'
    )


@pytest.mark.unit
@pytest.mark.parametrize("unsafe", [1.1, {1: "value"}, {"a": {1, 2}}, object()])
def test_fail_loud_on_unsafe_values(unsafe):
    with pytest.raises(TypeError):
        canonical_json(unsafe)


@pytest.mark.unit
def test_naive_datetimes_are_rejected():
    with pytest.raises(ValueError):
        canonical_json(datetime(2026, 10, 30, 7, 0))
