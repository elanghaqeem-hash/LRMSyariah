"""SIT-DQ: mixed source upload, cross-file reporting date, GL reference and gates."""
from __future__ import annotations

from copy import deepcopy
from datetime import date

from lrm_data.schema import DatasetType
from lrm_data.validation import validate_batch
from scripts.generate_synthetic_inputs import SAMPLES, workbook_bytes

CUTOFF = date(2026, 10, 30)


def sample_files() -> dict[str, bytes]:
    return {f"{d.value}.xlsx": workbook_bytes(d) for d in DatasetType}


def valid_batch(files: dict[str, bytes], **kwargs: object):
    return validate_batch(files, reporting_date=CUTOFF, reporting_currency="IDR",
                          required_datasets=list(DatasetType), **kwargs)


def test_full_13_source_batch_has_no_failures_but_mapping_warning() -> None:
    result = valid_batch(sample_files())
    assert len(result.sources) == 13
    assert result.report.status == "WARNING"
    assert not result.report.calculation_allowed  # Mapping approval is absent in WP1
    assert not result.report.submission_allowed
    assert all(f.severity.value == "WARNING" for f in result.report.findings)


def test_missing_mandatory_dataset_fails() -> None:
    files = sample_files(); del files["Deposito.xlsx"]
    result = valid_batch(files)
    assert result.report.status == "FAILED"
    assert any(f.dataset_type == "Deposito" for f in result.report.findings)


def test_mismatched_cutoff_fails() -> None:
    files = sample_files()
    files["Deposito.xlsx"] = workbook_bytes(DatasetType.DEPOSITO,
                                              meta_overrides={"reporting_date": date(2026,10,29)})
    result = valid_batch(files)
    assert any(f.rule_id == "DQ-DATE-001" for f in result.report.findings)


def test_reporting_currency_mismatch_fails_no_automatic_fx() -> None:
    files = sample_files()
    files["Deposito.xlsx"] = workbook_bytes(DatasetType.DEPOSITO,
                                              meta_overrides={"reporting_currency":"USD"})
    assert any(f.rule_id == "DQ-CURRENCY-001" for f in valid_batch(files).report.findings)


def test_duplicate_business_key_fails() -> None:
    files = sample_files()
    rows = deepcopy(SAMPLES[DatasetType.GIRO_TABUNGAN]); rows.append(deepcopy(rows[0]))
    files["GiroTabungan.xlsx"] = workbook_bytes(DatasetType.GIRO_TABUNGAN, rows)
    assert any(f.rule_id == "DQ-DUP-001" for f in valid_batch(files).report.findings)


def test_missing_gl_anchor_reference_fails() -> None:
    files = sample_files()
    rows = deepcopy(SAMPLES[DatasetType.GIRO_TABUNGAN]); rows[0]["gl_code"] = "GL-UNKNOWN"
    files["GiroTabungan.xlsx"] = workbook_bytes(DatasetType.GIRO_TABUNGAN, rows)
    assert any(f.rule_id == "DQ-REF-001" for f in valid_batch(files).report.findings)


def test_matured_placement_fails() -> None:
    files = sample_files()
    rows = deepcopy(SAMPLES[DatasetType.PENEMPATAN_BANK_LAIN]); rows[0]["jatuh_tempo"] = date(2026,10,29)
    files["PenempatanBankLain.xlsx"] = workbook_bytes(DatasetType.PENEMPATAN_BANK_LAIN, rows)
    assert any(f.rule_id == "DQ-MATURITY-001" for f in valid_batch(files).report.findings)


def test_future_regulatory_reference_fails() -> None:
    files = sample_files()
    rows = deepcopy(SAMPLES[DatasetType.KEWAJIBAN_GWM_PLM]); rows[0]["tanggal_efektif"] = date(2026,11,1)
    files["KewajibanGWMPLM.xlsx"] = workbook_bytes(DatasetType.KEWAJIBAN_GWM_PLM, rows)
    assert any(f.rule_id == "DQ-MATURITY-001" for f in valid_batch(files).report.findings)


def test_unapproved_akad_blocks() -> None:
    files = sample_files()
    rows = deepcopy(SAMPLES[DatasetType.DEPOSITO]); rows[0]["akad"] = "other_pending_bank_approval"
    files["Deposito.xlsx"] = workbook_bytes(DatasetType.DEPOSITO, rows)
    assert any(f.rule_id == "DQ-AKAD-001" for f in valid_batch(files).report.findings)


def test_unknown_required_scope_is_warning() -> None:
    files = {"NeracaHarian.xlsx": workbook_bytes(DatasetType.NERACA_HARIAN)}
    result = validate_batch(files, reporting_date=CUTOFF, reporting_currency="IDR")
    assert result.report.status == "WARNING"
    assert any(f.rule_id == "DQ-SCOPE-001" for f in result.report.findings)


def test_duplicate_dataset_type_fails() -> None:
    files = sample_files(); files["NeracaHarian_duplicate.xlsx"] = files["NeracaHarian.xlsx"]
    assert any(f.rule_id == "DQ-DUP-001" for f in valid_batch(files).report.findings)


def test_source_row_currency_mismatch_fails() -> None:
    files = sample_files()
    rows = deepcopy(SAMPLES[DatasetType.GIRO_TABUNGAN]); rows[0]["currency"] = "USD"
    files["GiroTabungan.xlsx"] = workbook_bytes(DatasetType.GIRO_TABUNGAN, rows)
    assert any(f.rule_id == "DQ-CURRENCY-001" for f in valid_batch(files).report.findings)


def test_cross_dataset_product_akad_conflict_fails() -> None:
    files = sample_files()
    rows = deepcopy(SAMPLES[DatasetType.DISTRIBUSI_BAGI_HASIL]); rows[0]["akad"] = "wadiah"
    files["DistribusiBagiHasil.xlsx"] = workbook_bytes(DatasetType.DISTRIBUSI_BAGI_HASIL, rows)
    assert any(f.rule_id == "DQ-AKAD-003" for f in valid_batch(files).report.findings)
