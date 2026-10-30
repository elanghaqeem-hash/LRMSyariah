from datetime import date

import pytest

from lrm_engine.common.time_buckets import (
    TimeBucket, classify_days, remaining_days, validate_buckets,
)

BUCKETS = (TimeBucket("short", 0, 30), TimeBucket("long", 31, None))


@pytest.mark.unit
def test_bucket_classification():
    assert classify_days(0, BUCKETS) == "short"
    assert classify_days(30, BUCKETS) == "short"
    assert classify_days(31, BUCKETS) == "long"
    assert classify_days(1000, BUCKETS) == "long"
    assert remaining_days(date(2026, 10, 30), date(2026, 10, 31)) == 1


@pytest.mark.unit
def test_bucket_guard():
    with pytest.raises(ValueError):
        TimeBucket("", 0, 2)
    with pytest.raises(ValueError):
        TimeBucket("x", -1, 2)
    with pytest.raises(ValueError):
        TimeBucket("x", 2, 1)
    with pytest.raises(ValueError):
        TimeBucket("x", 0.5, 1)
    with pytest.raises(ValueError):
        TimeBucket(3, 0, 1)
    with pytest.raises(ValueError):
        TimeBucket("x", 1, True)
    with pytest.raises(ValueError):
        validate_buckets(())
    with pytest.raises(ValueError):
        validate_buckets((TimeBucket("x", 0, 2), TimeBucket("x", 3, 5)))
    with pytest.raises(ValueError):
        validate_buckets((TimeBucket("x", 0, 2), TimeBucket("y", 2, 4)))
    with pytest.raises(ValueError):
        validate_buckets((TimeBucket("x", 0, None), TimeBucket("y", 3, 4)))


@pytest.mark.unit
def test_unmapped_tenor_and_date_rejected():
    with pytest.raises(ValueError):
        classify_days(3, (TimeBucket("a", 0, 1), TimeBucket("b", 5, 10)))
    with pytest.raises(ValueError):
        classify_days(-1, BUCKETS)
    with pytest.raises(ValueError):
        classify_days(True, BUCKETS)
    with pytest.raises(ValueError):
        remaining_days(date(2026, 10, 30), date(2026, 10, 29))
