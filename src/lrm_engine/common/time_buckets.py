"""Externally defined maturity time buckets; rule: ENG-TIME-001.

Regulatory maturity boundaries MUST be provided from verified parameter snapshots.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence


@dataclass(frozen=True)
class TimeBucket:
    """Inclusive day range. `end_day=None` means open-ended."""

    name: str
    start_day: int
    end_day: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise ValueError("bucket name must be text")
        if (
            isinstance(self.start_day, bool)
            or not isinstance(self.start_day, int)
            or (self.end_day is not None and (isinstance(self.end_day, bool) or not isinstance(self.end_day, int)))
        ):
            raise ValueError("bucket bounds must be integers")
        if not self.name.strip() or self.start_day < 0:
            raise ValueError("bucket name must be nonblank, start_day >= 0")
        if self.end_day is not None and self.end_day < self.start_day:
            raise ValueError("end_day must be >= start_day")


def validate_buckets(buckets: Sequence[TimeBucket]) -> None:
    """Reject duplicate names or overlapping ranges; gaps are allowed but fail on classify."""
    if not buckets:
        raise ValueError("bucket configuration must not be empty")
    if len({b.name for b in buckets}) != len(buckets):
        raise ValueError("duplicate bucket name")
    ordered = sorted(buckets, key=lambda bucket: bucket.start_day)
    for previous, current in zip(ordered, ordered[1:]):
        if previous.end_day is None or current.start_day <= previous.end_day:
            raise ValueError("overlapping bucket ranges")


def classify_days(days: int, buckets: Sequence[TimeBucket]) -> str:
    """Classify without fallback; unmapped tenor is an explicit error."""
    if isinstance(days, bool) or not isinstance(days, int) or days < 0:
        raise ValueError("days must be a nonnegative integer")
    validate_buckets(buckets)
    for bucket in buckets:
        if days >= bucket.start_day and (bucket.end_day is None or days <= bucket.end_day):
            return bucket.name
    raise ValueError(f"no valid maturity bucket for days={days}")


def remaining_days(reporting_date: date, maturity_date: date) -> int:
    """Fail on past maturity; no implicit rollover or maturity adjustment."""
    difference = (maturity_date - reporting_date).days
    if difference < 0:
        raise ValueError("maturity is before reporting date")
    return difference
