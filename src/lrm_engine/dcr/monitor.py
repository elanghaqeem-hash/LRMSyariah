"""WP10 DCR exposure scenario for ALCO, not Bank nisbah/PER advice.

IFSB/POJK 20/2025 + Bank DPS policy [VERIFY] before deployment.
All coefficients, day count and targets require Bank approval; no defaults.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, localcontext
from lrm_engine.common.decimal_math import ENGINE_CONTEXT, as_decimal


@dataclass(frozen=True)
class DCRResult:
    rate_gap: Decimal
    additional_runoff: Decimal
    smoothing_cost: Decimal
    warning: bool
    methodology_status: str = 'ENGINEERING_UNVERIFIED'


def calculate_dcr(*, mudharabah_balance: Decimal, benchmark_rate: Decimal,
                  equivalent_rate: Decimal, tolerance: Decimal, beta: Decimal,
                  target_rate: Decimal, distributable_rate: Decimal,
                  time_days: int, day_count_basis: Decimal) -> DCRResult:
    """Compute scenario shocks; use no implicit bank policy, interest, nisbah or PER."""
    vals=[as_decimal(x) for x in (mudharabah_balance,benchmark_rate,equivalent_rate,
          tolerance,beta,target_rate,distributable_rate,day_count_basis)]
    balance, benchmark, equivalent, tol, b, target, distributable, basis=vals
    if any(x < 0 for x in vals) or any(x > 1 for x in (benchmark,equivalent,tol,b,target,distributable)):
        raise ValueError('Negative amount/rate or out-of-range rate')
    if basis <= 0 or isinstance(time_days,bool) or not isinstance(time_days,int) or time_days < 0:
        raise ValueError('Positive approved day-count basis and nonnegative days required')
    with localcontext(ENGINE_CONTEXT):
        gap=benchmark-equivalent
        runoff=b * max(Decimal(0),gap-tol) * balance
        smoothing=max(Decimal(0),target-distributable) * balance * Decimal(time_days)/basis
    return DCRResult(gap,runoff,smoothing,gap>tol)