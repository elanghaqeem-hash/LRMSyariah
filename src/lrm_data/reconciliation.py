"""WP5 R11: bank GL/detailed-source/engine three-layer reconciliation.

This is an engineering validation primitive; Bank must approve GL mapping, sign
convention, materiality and tolerance. No implicit zero or default tolerance.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Sequence

from lrm_engine.common.decimal_math import ENGINE_CONTEXT, as_decimal


@dataclass(frozen=True)
class ReconPolicy:
    tolerance: Decimal
    approval_ref: str
    legal_basis: str
    parameter_version: str

    def __post_init__(self) -> None:
        value = as_decimal(self.tolerance)
        if value < 0:
            raise ValueError("Bank-approved tolerance must be nonnegative")
        if any(not s.strip() or '[VERIFY]' in s.upper() or 'TBD' in s.upper()
               for s in (self.approval_ref, self.legal_basis, self.parameter_version)):
            raise ValueError("Reconciliation tolerance approval evidence is required")
        object.__setattr__(self, 'tolerance', value)


@dataclass(frozen=True)
class ReconEntry:
    gl_code: str
    amount: Decimal
    reporting_date: str

    def __post_init__(self) -> None:
        if not self.gl_code.strip() or not self.reporting_date.strip():
            raise ValueError("GL and reporting date required")
        object.__setattr__(self, 'amount', as_decimal(self.amount))


@dataclass(frozen=True)
class ReconLine:
    gl_code: str
    bank_gl: Decimal
    source_detail: Decimal
    engine_result: Decimal
    source_variance: Decimal
    engine_variance: Decimal
    status: str


@dataclass(frozen=True)
class ReconReport:
    status: str
    reporting_date: str
    lines: tuple[ReconLine, ...]
    parameter_version: str


def reconcile_three_layers(*, bank_gl: Sequence[ReconEntry],
                           source_detail: Sequence[ReconEntry],
                           engine_output: Sequence[ReconEntry],
                           policy: ReconPolicy) -> ReconReport:
    """Require complete GL coverage and exact declared reporting date across layers."""
    if not bank_gl or not source_detail or not engine_output:
        raise ValueError("All three populated reconciliation layers are mandatory")
    dates = {r.reporting_date for records in (bank_gl, source_detail, engine_output)
             for r in records}
    if len(dates) != 1:
        raise ValueError("Mixed reporting dates; reconciliation blocked")
    anchor: dict[str, Decimal] = {}
    for item in bank_gl:
        if item.gl_code in anchor:
            raise ValueError("Duplicate bank GL anchor")
        anchor[item.gl_code] = item.amount

    def aggregate(records: Sequence[ReconEntry]) -> dict[str, Decimal]:
        grouped: dict[str, Decimal] = {}
        with localcontext(ENGINE_CONTEXT):
            for row in records:
                grouped[row.gl_code] = grouped.get(row.gl_code, Decimal(0)) + row.amount
        return grouped

    details, engine = aggregate(source_detail), aggregate(engine_output)
    if set(anchor) != set(details) or set(anchor) != set(engine):
        raise ValueError("GL coverage mismatch; missing or unrecognized GL")
    lines = []
    for code in sorted(anchor):
        amount, raw, calc = anchor[code], details[code], engine[code]
        raw_diff, calc_diff = raw - amount, calc - raw
        status = ('PASS' if abs(raw_diff) <= policy.tolerance
                  and abs(calc_diff) <= policy.tolerance else 'FAILED')
        lines.append(ReconLine(code, amount, raw, calc, raw_diff, calc_diff, status))
    return ReconReport(status='PASS' if all(x.status == 'PASS' for x in lines) else 'FAILED',
                       reporting_date=next(iter(dates)), lines=tuple(lines),
                       parameter_version=policy.parameter_version)