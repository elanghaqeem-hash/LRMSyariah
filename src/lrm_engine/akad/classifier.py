"""DB/IO-independent akad classification; R02 and AKAD-CLASSIFY-001.

Regulatory category codes and mappings are supplied from Bank-approved records.
No sharia treatment, haircut, or regulatory assumption is inferred here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ApprovedMapping:
    dataset: str
    source_key: str
    akad: str
    balance_side: str
    lcr_category: str
    nsfr_category: str
    rule_id: str
    mapping_version: int
    effective_from: date
    effective_to: date | None
    syariah_review_ref: str


class MappingNotFound(ValueError):
    pass


def classify(*, dataset: str, source_key: str, akad: str, as_of: date,
             mapping: ApprovedMapping) -> tuple[str, str, int]:
    """Return LCR category, rule ID, mapping version for an exact match."""
    if (dataset != mapping.dataset or source_key != mapping.source_key or
        akad != mapping.akad or mapping.effective_from > as_of or
        (mapping.effective_to is not None and as_of > mapping.effective_to) or
        not mapping.rule_id or not mapping.lcr_category or not mapping.nsfr_category or
        not mapping.syariah_review_ref):
        raise MappingNotFound("No effective, approved mapping for the record")
    return mapping.lcr_category, mapping.rule_id, mapping.mapping_version
