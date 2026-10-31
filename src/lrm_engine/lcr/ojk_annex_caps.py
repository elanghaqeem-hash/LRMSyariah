"""POJK 20/2025 BUS/UUS Lampiran I, III.C: exact HQLA composition adjustment.

This pure arithmetic does not attest SFT asset eligibility or derive adjusted
levels from trade records. Upstream signed, matured-SFT evidence is mandatory
before any adjusted levels can be used operationally.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext

from lrm_engine.common.decimal_math import ENGINE_CONTEXT, as_decimal


@dataclass(frozen=True)
class HQLACapResult:
    """Post-haircut stock, two ordered composition deductions, final HQLA."""

    deduction_level2b: Decimal
    deduction_level2: Decimal
    total_hqla: Decimal
    included_level1: Decimal
    included_level2a: Decimal
    included_level2b: Decimal
    adjusted_level1: Decimal
    adjusted_level2a: Decimal
    adjusted_level2b: Decimal


def official_cap_adjustments(
    *, level1: Decimal, level2a: Decimal, level2b: Decimal,
    adjusted_level1: Decimal, adjusted_level2a: Decimal, adjusted_level2b: Decimal,
) -> HQLACapResult:
    """Calculate regulatory caps exactly as Lampiran I, Section III.C.1-2.

    All arguments are *post-haircut*. Adjusted levels represent SFT short-term
    unwind outcomes in III.C.3-6, not arbitrary manual corrections.
    Their independent bank-controlled transaction calculation is NOT provided
    by this function. Validation of SFT eligibility/maturity is upstream.
    """
    x = [as_decimal(t) for t in (level1, level2a, level2b,
                                 adjusted_level1, adjusted_level2a, adjusted_level2b)]
    if any(v < 0 or not v.is_finite() for v in x):
        raise ValueError("HQLA and adjusted HQLA levels must be finite and nonnegative")
    l1, l2a, l2b, a1, a2a, a2b = x
    with localcontext(ENGINE_CONTEXT):
        # Annex I III.C.1: greater of (a), (b), zero; (b) uses *stock* L1,
        # whereas (a) uses adjusted L1 and adjusted L2A.
        less_2b = max(
            a2b - (Decimal(15) / Decimal(85)) * (a1 + a2a),
            a2b - (Decimal(15) / Decimal(60)) * l1,
            Decimal(0),
        )
        # Annex I III.C.2: deduction AFTER 2B adjustment (not before).
        less_2 = max(a2a + a2b - less_2b - (Decimal(2) / Decimal(3)) * a1,
                     Decimal(0))
        l2a_kept = l2a - less_2
        l2b_kept = l2b - less_2b
        total = l1 + l2a_kept + l2b_kept
        if total < 0 or l2a_kept < 0 or l2b_kept < 0:
            raise ValueError("Adjusted HQLA deductions exceed eligible stock; verify SFT ledger")
        return HQLACapResult(
            deduction_level2b=less_2b, deduction_level2=less_2,
            total_hqla=total, included_level1=l1, included_level2a=l2a_kept,
            included_level2b=l2b_kept, adjusted_level1=a1,
            adjusted_level2a=a2a, adjusted_level2b=a2b,
        )