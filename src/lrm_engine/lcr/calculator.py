"""WP4 LCR computation core with fully supplied approved factor snapshot.

R01/R03/R04; POJK 20/2025 [VERIFY full BUS annex, HQLA unwind].
This is an engineering implementation; NOT yet certified for OJK reporting.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Mapping, Sequence
import re

from lrm_engine.lcr.ojk_annex_caps import official_cap_adjustments

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

    Annex I III.C applies 2B adjustment first, then total Level 2 adjustment.
    SFT unwind adjusted-stock extraction still requires bank trade evidence; any
    `has_unwind_transactions` is therefore blocked, not assumed to be zero.
    All outputs retain full Decimal precision; no rounding in core.
    """
    if has_unwind_transactions:
        raise ValueError("HQLA adjusted-unwind model not implemented; regulatory run blocked")
    with localcontext(ENGINE_CONTEXT):
        levels: dict[str, Decimal] = {level: Decimal(0) for level in HQLA_LEVELS}
        trace: list[tuple[str, str, Decimal]] = []
        for asset in hqla:
            haircut = _factor(factors, asset.factor_key)
            if asset.level == "L1" and haircut != Decimal(0):
                raise ValueError("Official POJK Level 1 must have zero haircut")
            if asset.level == "L2A" and haircut != Decimal("0.15"):
                raise ValueError("Official POJK Level 2A requires 15 percent haircut")
            effective = asset.amount * (Decimal(1) - haircut)
            levels[asset.level] += effective
            trace.append((asset.rule_id, asset.source_sha256, effective))
        one, a, b = (levels[n] for n in HQLA_LEVELS)
        cap_two = _factor(factors, "hqlacap.level2")
        cap_b = _factor(factors, "hqlacap.level2b")
        if cap_two != Decimal("0.40") or cap_b != Decimal("0.15"):
            raise ValueError("Official POJK L2 and L2B limits require 40/15 percent")
        # Annex I III.C.1–2 exact two-stage deduction, *after* asset haircuts.
        # No-SFT case: adjusted holdings equal the current eligible holdings.
        # SFT trades remain fail-closed until authenticated Bank collateral
        # ledgers supply eligible adjusted stock and independent evidence.
        capped = official_cap_adjustments(
            level1=one, level2a=a, level2b=b,
            adjusted_level1=one, adjusted_level2a=a, adjusted_level2b=b,
        )
        final_hqla = capped.total_hqla
        a_used, b_used = capped.included_level2a, capped.included_level2b
        out = Decimal(0)
        for outflow_leg in outflows:
            weighted = outflow_leg.amount * _factor(factors, outflow_leg.factor_key)
            out += weighted
            trace.append((outflow_leg.rule_id, outflow_leg.source_sha256, weighted))
        incoming = Decimal(0)
        for inflow_leg in inflows:
            weighted = inflow_leg.amount * _factor(factors, inflow_leg.factor_key)
            incoming += weighted
            trace.append((inflow_leg.rule_id, inflow_leg.source_sha256, weighted))
        inflow_cap = _factor(factors, "inflow.cap")
        inflow_used = min(incoming, inflow_cap * out)
        nco = out - inflow_used
        return LCRResult(hqla=final_hqla, outflow=out, inflow_raw=incoming,
                         inflow_used=inflow_used, net_cash_outflow=nco,
                         lcr=ratio(final_hqla, nco), level1=one, level2a=a_used,
                         level2b=b_used, trace=tuple(trace))