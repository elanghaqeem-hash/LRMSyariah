"""Strict differential checker against a separately approved Bank LCR working paper.

The comparison is executable for synthetic golden cases. Authentic Bank papers
require Bank-controlled ingestion, external signing and source-vault verification.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext
from typing import Any, Mapping

from lrm_engine.common.canonical import sha256_canonical
from lrm_engine.common.decimal_math import ENGINE_CONTEXT, as_decimal

_FIELDS = ("hqla", "outflow", "inflow_raw", "inflow_used", "net_cash_outflow", "lcr",
           "level1", "level2a", "level2b", "adjusted_level1", "adjusted_level2a",
           "adjusted_level2b")
_SHA = re.compile(r"[0-9a-f]{64}\Z")


class WorkingPaperError(ValueError):
    """Only non-sensitive validation errors, never Bank values or account IDs."""


@dataclass(frozen=True)
class BankWorkingPaper:
    reporting_date: date
    currency: str
    paper_sha256: str
    bank_approved_ref: str
    bank_approved_sha256: str
    measures: Mapping[str, Decimal]
    rule_amounts: Mapping[str, Decimal]
    synthetic_only: bool = True

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Z]{3}", self.currency):
            raise WorkingPaperError("Reporting paper currency must be ISO 4217")
        if not _SHA.fullmatch(self.paper_sha256) or not _SHA.fullmatch(self.bank_approved_sha256):
            raise WorkingPaperError("Working paper digest/approval digest missing")
        if not self.bank_approved_ref.strip():
            raise WorkingPaperError("Working paper must reference Bank approval")
        if set(self.measures) != set(_FIELDS) or not self.rule_amounts:
            raise WorkingPaperError("Missing or extra LCR measure/rule classification")
        for group in (self.measures, self.rule_amounts):
            for name, value in group.items():
                if not name.strip() or not as_decimal(value).is_finite():
                    raise WorkingPaperError("Invalid named working paper value")
        if any(as_decimal(v) < 0 for v in self.measures.values()):
            raise WorkingPaperError("Bank paper summary metrics must be nonnegative")


@dataclass(frozen=True)
class Difference:
    category: str
    bank: Decimal
    engine: Decimal
    delta: Decimal
    tolerance: Decimal
    status: str


@dataclass(frozen=True)
class DifferentialResult:
    status: str
    reporting_date: date
    currency: str
    paper_sha256: str
    engine_result_sha256: str
    differences: tuple[Difference, ...]
    evidence_sha256: str
    methodology_status: str = "INDEPENDENT_BANK_APPROVAL_PENDING"


def parse_working_paper_bytes(data: bytes, *, expected_sha256: str,
                              approved_ref: str, bank_approved_sha256: str,
                              synthetic_only: bool) -> BankWorkingPaper:
    """Validate raw working-paper bytes against independently supplied SHA.

    Restrict to Bank-provided, machine-readable summary JSON: no PII, no XLSX
    macro execution. This does not itself verify the Bank digital signature.
    """
    if len(data) > 2_000_000 or not _SHA.fullmatch(expected_sha256):
        raise WorkingPaperError("Working paper size or source digest invalid")
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise WorkingPaperError("Working paper bytes differ from approved reference")
    try:
        paper: Any = json.loads(data, parse_float=Decimal)
        if set(paper) != {"reporting_date", "currency", "measures", "rule_amounts"}:
            raise WorkingPaperError("Paper requires exact agreed structured fields")
        if not isinstance(paper["measures"], dict) or not isinstance(paper["rule_amounts"], dict):
            raise WorkingPaperError("Invalid working paper metric dictionaries")
        return BankWorkingPaper(
            reporting_date=date.fromisoformat(paper["reporting_date"]),
            currency=paper["currency"], paper_sha256=expected_sha256,
            bank_approved_ref=approved_ref, bank_approved_sha256=bank_approved_sha256,
            measures={k: as_decimal(v) for k, v in paper["measures"].items()},
            rule_amounts={k: as_decimal(v) for k, v in paper["rule_amounts"].items()},
            synthetic_only=synthetic_only,
        )
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        raise WorkingPaperError("Invalid, noncanonical or incomplete Bank working paper") from exc


def compare_working_paper(*, bank: BankWorkingPaper, engine: Mapping[str, Any],
                          reporting_date: date, currency: str,
                          monetary_tolerance: Decimal, ratio_tolerance: Decimal,
                          tolerance_approval_ref: str) -> DifferentialResult:
    """Fail missing/extra rule rows, valuation mismatch, dates and unexplained deltas.

    A synthetic PASS means only matching arithmetic, NOT Bank certification.
    """
    if bank.reporting_date != reporting_date or bank.currency != currency:
        raise WorkingPaperError("Bank/engine cut-off or currency differs")
    if (not tolerance_approval_ref.strip() or "[VERIFY]" in tolerance_approval_ref.upper()
            or "TBD" in tolerance_approval_ref.upper()):
        raise WorkingPaperError("Independently approved tolerances required")
    monetary = as_decimal(monetary_tolerance)
    rat = as_decimal(ratio_tolerance)
    if monetary < 0 or rat < 0:
        raise WorkingPaperError("Variance tolerances cannot be negative")
    if not all(k in engine for k in _FIELDS) or "trace" not in engine:
        raise WorkingPaperError("Engine result lacks mandatory trace or adjusted stock")
    with localcontext(ENGINE_CONTEXT):
        rule_totals: dict[str, Decimal] = {}
        for entry in engine["trace"]:
            if len(entry) != 3 or not isinstance(entry[0], str) or not _SHA.fullmatch(entry[1]):
                raise WorkingPaperError("Invalid engine rule-level evidence trace")
            rule_totals[entry[0]] = rule_totals.get(entry[0], Decimal(0)) + as_decimal(entry[2])
        if set(rule_totals) != set(bank.rule_amounts):
            raise WorkingPaperError("Unmatched or extra working paper regulatory classification")
        diffs: list[Difference] = []
        for name in _FIELDS:
            amount = as_decimal(engine[name])
            b = as_decimal(bank.measures[name])
            tol = rat if name == "lcr" else monetary
            diffs.append(Difference(name, b, amount, amount - b, tol,
                                    "PASS" if abs(amount - b) <= tol else "FAILED"))
        for name in sorted(rule_totals):
            amount = rule_totals[name]
            b = as_decimal(bank.rule_amounts[name])
            diffs.append(Difference("RULE:" + name, b, amount, amount - b, monetary,
                                    "PASS" if abs(amount - b) <= monetary else "FAILED"))
        status = "PASS" if all(d.status == "PASS" for d in diffs) else "FAILED"
        digest = sha256_canonical({"status": status, "reporting_date": reporting_date,
             "currency": currency, "paper": bank.paper_sha256, "bank_approval": bank.bank_approved_sha256,
             "engine": sha256_canonical(engine), "differences": diffs,
             "tolerance_approval": tolerance_approval_ref})
        return DifferentialResult(status=status, reporting_date=reporting_date,
            currency=currency, paper_sha256=bank.paper_sha256,
            engine_result_sha256=sha256_canonical(engine), differences=tuple(diffs),
            evidence_sha256=digest)