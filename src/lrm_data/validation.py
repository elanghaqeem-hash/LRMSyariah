"""Batch data quality, source reconciliation prerequisites, and submission gates.

Rules: DQ-DATE, DQ-CURRENCY, DQ-DUP, DQ-REF, DQ-MATURITY, DQ-AKAD.
This is NOT a regulatory LCR/NSFR calculation (WP4/WP8) or GL recon (WP5).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping, Sequence

from lrm_data.dq import DQReport, Finding
from lrm_data.loader import LoadedSource, load_xlsx
from lrm_data.schema import DatasetType, Akad


@dataclass(frozen=True)
class BatchResult:
    sources: tuple[LoadedSource, ...]
    report: DQReport


def validate_batch(files: Mapping[str, bytes], *, reporting_date: date,
                   reporting_currency: str,
                   required_datasets: Sequence[DatasetType] | None = None) -> BatchResult:
    """Validate all supplied Excel sources against one cut-off and allowed dataset set.

    Mapping/parameter approval is not accepted as a caller-supplied boolean:
    WP2 must supply a signed, effective-dated approved mapping service.
    """
    findings: list[Finding] = []
    loaded: list[LoadedSource] = []
    seen_types: set[DatasetType] = set()
    product_akad: dict[str, Akad] = {}
    for file_name, blob in sorted(files.items()):
        result = load_xlsx(file_name, blob)
        findings.extend(result.findings)
        if result.source is None:
            continue
        source = result.source
        loaded.append(source)
        meta = source.metadata
        typ = meta.dataset_type
        if typ in seen_types:
            findings.append(Finding("DQ-DUP-001", typ.value, None, None,
                                    "Multiple files for the same dataset type", source.file_hash))
        seen_types.add(typ)
        if meta.reporting_date != reporting_date:
            findings.append(Finding("DQ-DATE-001", typ.value, None, "reporting_date",
                                    "Reporting date does not match batch cut-off", source.file_hash))
        if meta.reporting_currency != reporting_currency:
            findings.append(Finding("DQ-CURRENCY-001", typ.value, None,
                                    "reporting_currency", "Currency mismatch; verified FX mapping unavailable",
                                    source.file_hash))
        model = type(source.rows[0].record) if source.rows else None
        if model is not None and "akad" in model.model_fields:
            findings.append(Finding("DQ-AKAD-002", typ.value, None, "akad",
                                    "WP2 approved product-to-akad/category mapping is pending",
                                    source.file_hash))
        keys: set[str] = set()
        for item in source.rows:
            record = item.record
            if record.currency != meta.reporting_currency:
                findings.append(Finding("DQ-CURRENCY-001", typ.value, item.excel_row,
                                        "currency", "Row currency differs from file currency; FX unavailable",
                                        source.file_hash))
            product_code = getattr(record, "product_code", None)
            akad_for_product = getattr(record, "akad", None)
            if product_code is not None and akad_for_product is not None:
                previous = product_akad.setdefault(product_code, akad_for_product)
                if previous is not akad_for_product:
                    findings.append(Finding("DQ-AKAD-003", typ.value, item.excel_row, "akad",
                                            "One product code has conflicting akad values",
                                            source.file_hash))
            key = str(getattr(record, type(record).unique_key))
            if key in keys:
                findings.append(Finding("DQ-DUP-001", typ.value, item.excel_row,
                                        type(record).unique_key, "Duplicate source business key",
                                        source.file_hash))
            keys.add(key)
            akad = getattr(record, "akad", None)
            if akad is Akad.OTHER_PENDING_BANK_APPROVAL:
                findings.append(Finding("DQ-AKAD-001", typ.value, item.excel_row, "akad",
                                        "Unapproved akad value blocks calculations", source.file_hash))
            maturity = getattr(record, "jatuh_tempo", None)
            if maturity is not None and maturity < reporting_date:
                severity_rule = ("DQ-MATURITY-002" if typ is DatasetType.PEMBIAYAAN
                                 else "DQ-MATURITY-001")
                findings.append(Finding(severity_rule, typ.value, item.excel_row,
                                        "jatuh_tempo", "Maturity is before reporting date",
                                        source.file_hash))
            ref_date = getattr(record, "tanggal_efektif", None)
            if ref_date is not None and ref_date > reporting_date:
                findings.append(Finding("DQ-MATURITY-001", typ.value, item.excel_row,
                                        "tanggal_efektif", "Reference effective date lies in future",
                                        source.file_hash))
            schedule = getattr(record, "jadwal_angsuran", ())
            if any(instalment.tanggal < reporting_date for instalment in schedule):
                findings.append(Finding("DQ-MATURITY-002", typ.value, item.excel_row,
                                        "jadwal_angsuran", "Payment schedule includes a past date",
                                        source.file_hash))
    if required_datasets is None:
        findings.append(Finding("DQ-SCOPE-001", None, None, None,
                                "Required file set not signed off by Bank"))
    else:
        for missing in sorted(set(required_datasets) - seen_types):
            findings.append(Finding("DQ-SCHEMA-001", missing.value, None, None,
                                    "Mandatory dataset is absent"))
    gl_anchor = next((src for src in loaded if src.metadata.dataset_type is DatasetType.NERACA_HARIAN), None)
    if gl_anchor is not None:
        gl_codes = {item.record.gl_code for item in gl_anchor.rows}  # type: ignore[attr-defined]
        for src in loaded:
            if src is gl_anchor:
                continue
            for item in src.rows:
                gl_code = getattr(item.record, "gl_code", None)
                if gl_code is not None and gl_code not in gl_codes:
                    findings.append(Finding("DQ-REF-001", src.metadata.dataset_type.value,
                                            item.excel_row, "gl_code",
                                            "GL reference not present in NeracaHarian",
                                            src.file_hash))
    counts = {src.metadata.dataset_type.value: len(src.rows) for src in loaded}
    return BatchResult(tuple(loaded), DQReport(tuple(findings), counts, len(files)))
