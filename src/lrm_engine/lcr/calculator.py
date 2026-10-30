"""WP4 LCR computation core with fully supplied approved factor snapshot.

R01/R03/R04; POJK 20/2025 [VERIFY full BUS annex, HQLA unwind].
This is an engineering implementation; NOT yet certified for OJK reporting.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Mapping, Sequence
import re

from lrm_engine.common.decimal_math import ENGINE_CONTEXT, as_decimal, ratio

HASH64 = re.compile(r"[0-9a-f]{64}\Z")
HQLA_LEVELS = ("L1", "L2A", "L2B")


@dataclass(frozen=True)
class Factor:
    """External governed effective-dated parameter; no embedded regulatory number."""

    value: Decimal
    rule_id: str
    legal_basis: str
    approved_revision: str
    verification_ref: str
    status: str = "ACTIVE"

    def __post_init__(self) -> None:
        val = as_decimal(self.value)
        if val < 0 or val > 1:
            raise ValueError("Factor must be between zero and one")
        if self.status != "ACTIVE":
            raise ValueError("Inactive or unverified regulatory factor")
        if any(not s.strip() or "[VERIFY]" in s.upper() or "TBD" in s.upper()
               for s in (self.rule_id, self.legal_basis, self.approved_revision,
                         self.verification_ref)):
            raise ValueError("Approved provenance of factor is required")
        object.__setattr__(self, "value", val)


@dataclass(frozen=True)
class RegulatoryLeg:
    """Akad-first preclassified line with source file SHA; no borrower PII."""

    amount: Decimal
    akad: str
    rule_id: str
    source_sha256: str
    factor_key: str

    def __post_init__(self) -> None:
        amount = as_decimal(self.amount)
        if amount < 0 or not self.akad.strip() or not self.rule_id.strip():
            raise ValueError("Invalid amount/akad/rule")
        if not HASH64.fullmatch(self.source_sha256):
            raise ValueError("Valid source SHA-256 required")
        if not self.factor_key.strip():
            raise ValueError("Factor key missing")
        object.__setattr__(self, "amount", amount)


@dataclass(frozen=True)
class HQLALeg(RegulatoryLeg):
    level: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.level not in HQLA_LEVELS:
            raise ValueError("HQLA level must be explicitly classified")


@dataclass(frozen=True)
class LCRResult:
    hqla: Decimal
    outflow: Decimal
    inflow_raw: Decimal
    inflow_used: Decimal
    net_cash_outflow: Decimal
    lcr: Decimal
    level1: Decimal
    level2a: Decimal
    level2b: Decimal
    trace: tuple[tuple[str, str, Decimal], ...]
    methodology_status: str = "ENGINEERING_UNVERIFIED"


def _factor(factors: Mapping[str, Factor], key: str) -> Decimal:
    f = factors.get(key)
    if f is None or f.status != "ACTIVE":
        raise ValueError(f"Approved regulatory factor missing: {key}")
    return f.value


def calculate_lcr(*, hqla: Sequence[HQLALeg], outflows: Sequence[RegulatoryLeg],
                  inflows: Sequence[RegulatoryLeg], factors: Mapping[str, Factor],
                  has_unwind_transactions: bool) -> LCRResult:
    """Compute LCR, fail if composition must reflect unsettled short-term unwind.

    HQLA 2A is allocated before 2B when both composition caps bind. This
    allocation policy and exact adjusted-unwind treatment require independent
    signoff against POJK 20/2025 Annex before live bank reporting.
    All outputs retain full Decimal precision; no rounding in core.
    """
    if has_unwind_transactions:
        raise ValueError("HQLA adjusted-unwind model not implemented; regulatory run blocked")
    with localcontext(ENGINE_CONTEXT):
        levels: dict[str, Decimal] = {level: Decimal(0) for level in HQLA_LEVELS}
        trace: list[tuple[str, str, Decimal]] = []
        for item in hqla:
            haircut = _factor(factors, item.factor_key)
            effective = item.amount * (Decimal(1) - haircut)
            levels[item.level] += effective
            trace.append((item.rule_id, item.source_sha256, effective))
        one, a, b = (levels[n] for n in HQLA_LEVELS)
        cap_two = _factor(factors, "hqlacap.level2")
        cap_b = _factor(factors, "hqlacap.level2b")
        if cap_two >= 1 or cap_b >= 1:
            raise ValueError("Level 2 and 2B caps must be strictly below 1")
        if cap_b > cap_two:
            raise ValueError("Level 2B cap cannot exceed aggregate Level 2 cap")
        # Both cap limits are on POST-haircut HQLA (no unwind case).
        allowed_level2 = one * cap_two / (Decimal(1) - cap_two)
        a_used = min(a, allowed_level2)
        b_used = min(b, allowed_level2 - a_used,
                     (one + a_used) * cap_b / (Decimal(1) - cap_b))
        final_hqla = one + a_used + b_used
        out = Decimal(0)
        for item in outflows:
            weighted = item.amount * _factor(factors, item.factor_key)
            out += weighted
            trace.append((item.rule_id, item.source_sha256, weighted))
        incoming = Decimal(0)
        for item in inflows:
            weighted = item.amount * _factor(factors, item.factor_key)
            incoming += weighted
            trace.append((item.rule_id, item.source_sha256, weighted))
        inflow_cap = _factor(factors, "inflow.cap")
        inflow_used = min(incoming, inflow_cap * out)
        nco = out - inflow_used
        return LCRResult(hqla=final_hqla, outflow=out, inflow_raw=incoming,
                         inflow_used=inflow_used, net_cash_outflow=nco,
                         lcr=ratio(final_hqla, nco), level1=one, level2a=a_used,
                         level2b=b_used, trace=tuple(trace))