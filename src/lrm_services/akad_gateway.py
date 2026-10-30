"""WP1-to-WP2 approved mapping gate; R02, R10, DQ-AKAD-002/004.

This adapter can resolve WP1's provisional mapping warnings only when every
akad-bearing source record is mapped by an independently approved effective row.
It does not unlock production LCR calculation (WP4 remains unimplemented).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping, Sequence

from lrm_data.dq import DQReport, Finding
from lrm_data.schema import DatasetType
from lrm_data.validation import BatchResult, validate_batch
from lrm_engine.akad.classifier import classify, MappingNotFound
from lrm_services.governance import GovernanceService

SOURCE_KEY_FIELDS: dict[DatasetType, str] = {
    DatasetType.PENEMPATAN_BI: "jenis",
    DatasetType.SURAT_BERHARGA_SYARIAH: "jenis",
    DatasetType.PENEMPATAN_BANK_LAIN: "counterparty_code",  # Bank must verify mapping key
    DatasetType.GIRO_TABUNGAN: "product_code",
    DatasetType.DEPOSITO: "product_code",
    DatasetType.KEWAJIBAN_ANTARBANK: "counterparty_code",
    DatasetType.PEMBIAYAAN: "product_code",
    DatasetType.KONTINJENSI: "jenis",
    DatasetType.DISTRIBUSI_BAGI_HASIL: "product_code",
}


@dataclass(frozen=True)
class MappingTrace:
    dataset: str
    excel_row: int
    rule_id: str
    mapping_version: int
    lcr_category: str
    nsfr_category: str
    source_file_hash: str
    # No account/customer identifiers, amounts or personal data in the trace.


@dataclass(frozen=True)
class MappedBatch:
    batch: BatchResult
    mapping_traces: tuple[MappingTrace, ...]
    parameter_set_hash: str | None


def validate_batch_with_mapping(
    files: Mapping[str, bytes], *, service: GovernanceService,
    reporting_date: date, reporting_currency: str,
    required_datasets: Sequence[DatasetType] | None = None,
    required_parameter_ids: Sequence[str] | None = None,
) -> MappedBatch:
    """Fail on missing/inapplicable approved mapping; no caller-supplied approval flag."""
    initial = validate_batch(files, reporting_date=reporting_date,
                             reporting_currency=reporting_currency,
                             required_datasets=required_datasets)
    # Other DQ failures are preserved even when mapping passes.
    findings = [f for f in initial.report.findings if f.rule_id != "DQ-AKAD-002"]
    traces: list[MappingTrace] = []
    parameter_hash: str | None = None
    try:
        if required_parameter_ids is None:
            raise ValueError("Bank has not approved mandatory parameter scope")
        _, parameter_hash = service.parameter_snapshot(list(required_parameter_ids), reporting_date)
    except ValueError:
        findings.append(Finding("DQ-PARAM-001", None, None, "parameters",
                                "Mandatory approved regulatory parameter set unavailable"))
    for source in initial.sources:
        dataset = source.metadata.dataset_type
        for row in source.rows:
            record = row.record
            if not hasattr(record, "akad"):
                continue  # GL, capital, reference rate and GWM are not akad-bearing
            field = SOURCE_KEY_FIELDS.get(dataset)
            source_key = getattr(record, field, None) if field is not None else None
            akad = getattr(record, "akad", None)
            approved = (service.mapping(dataset.value, str(source_key), reporting_date)
                        if source_key else None)
            if approved is None:
                findings.append(Finding("DQ-AKAD-004", dataset.value, row.excel_row,
                                        field or "akad", "No approved, effective mapping",
                                        source.file_hash))
                continue
            try:
                lcr_cat, rule_id, version = classify(
                    dataset=dataset.value, source_key=str(source_key),
                    akad=akad.value, as_of=reporting_date, mapping=approved)
            except MappingNotFound:
                findings.append(Finding("DQ-AKAD-004", dataset.value, row.excel_row,
                                        "akad", "Approved mapping does not match source akad",
                                        source.file_hash))
                continue
            traces.append(MappingTrace(dataset.value, row.excel_row, rule_id,
                                       version, lcr_cat, approved.nsfr_category, source.file_hash))
    return MappedBatch(BatchResult(initial.sources,
                                  DQReport(tuple(findings), initial.report.counts,
                                           initial.report.checked_files)), tuple(traces), parameter_hash)
