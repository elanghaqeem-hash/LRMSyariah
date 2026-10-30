"""WP9 survival ladder: 19 externally-defined buckets (R08), ILAAP [VERIFY]."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Sequence

from lrm_engine.common.decimal_math import ENGINE_CONTEXT, as_decimal
from lrm_engine.common.time_buckets import TimeBucket, classify_days, validate_buckets


@dataclass(frozen=True)
class DatedCashFlow:
    day: int
    inflow: Decimal
    outflow: Decimal

    def __post_init__(self) -> None:
        if isinstance(self.day, bool) or not isinstance(self.day, int) or self.day < 0:
            raise ValueError('Invalid cash flow maturity day')
        inflow, outflow = as_decimal(self.inflow), as_decimal(self.outflow)
        if inflow < 0 or outflow < 0:
            raise ValueError('Negative non-netted cash flows forbidden')
        object.__setattr__(self,'inflow',inflow)
        object.__setattr__(self,'outflow',outflow)


@dataclass(frozen=True)
class SurvivalStep:
    bucket: str
    start_day: int
    end_day: int | None
    inflow: Decimal
    outflow: Decimal
    cumulative_position: Decimal


@dataclass(frozen=True)
class SurvivalResult:
    survival_days: int | None
    critical_bucket: str | None
    steps: tuple[SurvivalStep,...]
    breach: bool
    methodology_status: str = 'ENGINEERING_UNVERIFIED'


def calculate_survival(*, opening_buffer: Decimal, cashflows: Sequence[DatedCashFlow],
                       buckets: Sequence[TimeBucket], tolerance: Decimal,
                       require_nineteen: bool = True) -> SurvivalResult:
    """Find first cumulative-liquidity threshold breach; no implicit bucket defaults."""
    validate_buckets(buckets)
    if require_nineteen and len(buckets) != 19:
        raise ValueError('Bank approved 19-bucket configuration required')
    opening, threshold = as_decimal(opening_buffer), as_decimal(tolerance)
    if opening < 0 or threshold < 0:
        raise ValueError('Opening buffer and tolerance must be nonnegative')
    aggregated = {bucket.name: [Decimal(0),Decimal(0)] for bucket in buckets}
    for leg in cashflows:
        name = classify_days(leg.day,buckets)
        aggregated[name][0] += leg.inflow
        aggregated[name][1] += leg.outflow
    steps = []
    first_day: int | None = None
    first_bucket: str | None = None
    with localcontext(ENGINE_CONTEXT):
        current = opening
        for bucket in sorted(buckets,key=lambda b:b.start_day):
            incoming, outgoing = aggregated[bucket.name]
            current += incoming - outgoing
            steps.append(SurvivalStep(bucket.name,bucket.start_day,bucket.end_day,
                                      incoming,outgoing,current))
            if first_bucket is None and current < threshold:
                first_day,first_bucket = bucket.start_day,bucket.name
    return SurvivalResult(first_day,first_bucket,tuple(steps),first_bucket is not None)