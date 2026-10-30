"""Data quality rule registry and safe-to-log findings; control R10 / SIT-DQ.

Legal basis: project engineering control; Bank DQ tolerance approval pending WP2.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal


class Severity(StrEnum):
    FAILED = "FAILED"
    WARNING = "WARNING"


@dataclass(frozen=True)
class Rule:
    rule_id: str
    description: str
    owner: str
    severity: Severity


RULES: dict[str, Rule] = {
    r.rule_id: r for r in (
        Rule("DQ-FILE-001", "Valid permitted Excel .xlsx container", "IT/Data Owner", Severity.FAILED),
        Rule("DQ-SCHEMA-001", "Metadata, header, row schema and version", "Data Owner", Severity.FAILED),
        Rule("DQ-VAL-001", "Valid typed record, Decimal and data ranges", "Data Owner", Severity.FAILED),
        Rule("DQ-DATE-001", "All files share one reporting date", "SKMR", Severity.FAILED),
        Rule("DQ-CURRENCY-001", "One reporting currency; FX requires verified conversion", "Treasury", Severity.FAILED),
        Rule("DQ-DUP-001", "Unique business keys per dataset", "Data Owner", Severity.FAILED),
        Rule("DQ-REF-001", "Required on-balance GL key exists in anchor", "Finance", Severity.FAILED),
        Rule("DQ-MATURITY-001", "Maturity and rate reference dates are consistent", "SKMR", Severity.FAILED),
        Rule("DQ-AKAD-001", "Akad value populated and known in provisional vocabulary", "Sharia Compliance", Severity.FAILED),
        Rule("DQ-AKAD-002", "Product/akad regulatory mapping awaits WP2 approval", "Sharia Compliance", Severity.WARNING),
        Rule("DQ-AKAD-003", "Product code is associated with consistent akad", "Sharia Compliance", Severity.FAILED),
        Rule("DQ-AKAD-004", "Each akad-bearing record requires an effective approved regulatory mapping", "Sharia Compliance", Severity.FAILED),
        Rule("DQ-PARAM-001", "All required regulatory parameter IDs must resolve to approved effective versions", "SKMR", Severity.FAILED),
        Rule("DQ-MATURITY-002", "Overdue financing maturity to be reviewed", "SKMR", Severity.WARNING),
        Rule("DQ-SCOPE-001", "Required dataset set determined and supplied by Bank", "Data Owner", Severity.WARNING),
    )
}


@dataclass(frozen=True)
class Finding:
    rule_id: str
    dataset_type: str | None
    row: int | None
    field: str | None
    message: str  # Never include sensitive source data in error messages
    file_hash: str | None = None
    severity: Severity = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "severity", RULES[self.rule_id].severity)


@dataclass(frozen=True)
class DQReport:
    findings: tuple[Finding, ...] = ()
    counts: dict[str, int] = field(default_factory=dict)
    checked_files: int = 0

    @property
    def status(self) -> Literal["PASS", "WARNING", "FAILED"]:
        if any(f.severity is Severity.FAILED for f in self.findings):
            return "FAILED"
        if self.findings:
            return "WARNING"
        return "PASS"

    @property
    def calculation_allowed(self) -> bool:
        return self.status != "FAILED" and not any(
            f.rule_id == "DQ-AKAD-002" for f in self.findings
        )

    @property
    def submission_allowed(self) -> bool:
        # Bank must resolve all warnings and approve mappings through WP2.
        return self.status == "PASS"

    def summary(self) -> dict[str, object]:
        return {
            "status": self.status,
            "checked_files": self.checked_files,
            "record_counts": dict(sorted(self.counts.items())),
            "failed": sum(f.severity is Severity.FAILED for f in self.findings),
            "warnings": sum(f.severity is Severity.WARNING for f in self.findings),
            "calculation_allowed": self.calculation_allowed,
            "submission_allowed": self.submission_allowed,
        }
