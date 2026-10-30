"""WP9 parameter-driven stress overlays, preliminary ILAAP quantitative support.

No built-in shock percentages. All scenarios require Bank-approved provenance.
Regulatory stress assumptions and syariah models: [VERIFY] before official use.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, localcontext
from typing import Mapping, Sequence

from lrm_engine.common.decimal_math import ENGINE_CONTEXT, as_decimal
from lrm_engine.lcr.calculator import Factor, HQLALeg, LCRResult, RegulatoryLeg, calculate_lcr


@dataclass(frozen=True)
class StressScenario:
    name: str
    approved_version: str
    review_reference: str
    hqla_value_multiplier: Decimal
    outflow_multiplier: Decimal
    inflow_realisation: Decimal

    def __post_init__(self) -> None:
        for key in ('name', 'approved_version', 'review_reference'):
            text = getattr(self, key)
            if not text.strip() or '[VERIFY]' in text.upper() or 'TBD' in text.upper():
                raise ValueError('Bank-reviewed stress scenario reference required')
        for key in ('hqla_value_multiplier', 'outflow_multiplier', 'inflow_realisation'):
            value = as_decimal(getattr(self, key))
            if value < 0:
                raise ValueError('Stress values must not be negative')
            if key != 'outflow_multiplier' and value > 1:
                raise ValueError('This scenario multiplier must be between 0 and 1')
            object.__setattr__(self, key, value)


def stressed_lcr(*, scenario: StressScenario, hqla: Sequence[HQLALeg],
                 outflows: Sequence[RegulatoryLeg], inflows: Sequence[RegulatoryLeg],
                 factors: Mapping[str, Factor], has_unwind_transactions: bool) -> LCRResult:
    """Apply market value, withdrawal and inflow shocks before base LCR engine."""
    with localcontext(ENGINE_CONTEXT):
        adjusted_hqla = [replace(x, amount=x.amount * scenario.hqla_value_multiplier)
                         for x in hqla]
        adjusted_outflows = [replace(x, amount=x.amount * scenario.outflow_multiplier)
                             for x in outflows]
        adjusted_inflows = [replace(x, amount=x.amount * scenario.inflow_realisation)
                            for x in inflows]
    return calculate_lcr(hqla=adjusted_hqla, outflows=adjusted_outflows,
                         inflows=adjusted_inflows, factors=factors,
                         has_unwind_transactions=has_unwind_transactions)