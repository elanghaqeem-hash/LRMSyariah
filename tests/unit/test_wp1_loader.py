"""UT-WP1-LOAD: ingestion safeguards and row-level failures."""
from __future__ import annotations

import io
import zipfile
from copy import deepcopy

import pytest
from openpyxl import load_workbook

from lrm_data.loader import load_xlsx
from lrm_data.schema import DatasetType
from scripts.generate_synthetic_inputs import SAMPLES, workbook_bytes


def mutate(payload: bytes, fn: object) -> bytes:
    wb = load_workbook(io.BytesIO(payload))
    assert callable(fn)
    fn(wb)
    out = io.BytesIO()
    wb.save(out)
    wb.close()
    return out.getvalue()


@pytest.mark.parametrize("dataset", list(DatasetType))
def test_roundtrip_all_dataset_types(dataset: DatasetType) -> None:
    result = load_xlsx(f"{dataset.value}.xlsx", workbook_bytes(dataset))
    assert result.source is not None
    assert not result.findings
    assert result.source.metadata.dataset_type is dataset
    assert len(result.file_hash) == 64


def test_invalid_extension_fails() -> None:
    assert load_xlsx("test.xlsm", workbook_bytes(DatasetType.NERACA_HARIAN)).source is None
    assert load_xlsx("../test.xlsx", workbook_bytes(DatasetType.NERACA_HARIAN)).source is None
    assert load_xlsx("..\\test.xlsx", workbook_bytes(DatasetType.NERACA_HARIAN)).source is None


def test_corrupt_archive_fails() -> None:
    result = load_xlsx("corrupt.xlsx", b"bogus")
    assert result.source is None
    assert result.findings


def test_formula_fails_closed() -> None:
    payload = workbook_bytes(DatasetType.NERACA_HARIAN)
    bad = mutate(payload, lambda wb: setattr(wb["data"]["C2"], "value", "=1+1"))
    result = load_xlsx("invalid.xlsx", bad)
    assert result.source is None


def test_hidden_row_fails_closed() -> None:
    payload = workbook_bytes(DatasetType.NERACA_HARIAN)
    bad = mutate(payload, lambda wb: setattr(wb["data"].row_dimensions[2], "hidden", True))
    assert load_xlsx("hidden.xlsx", bad).source is None


def test_duplicate_header_fails_closed() -> None:
    payload = workbook_bytes(DatasetType.NERACA_HARIAN)
    bad = mutate(payload, lambda wb: setattr(wb["data"]["A1"], "value", "gl_code"))
    assert load_xlsx("dupe.xlsx", bad).source is None


def test_row_with_binary_float_not_accepted() -> None:
    # The loader must not quietly admit .xlsx numeric float money as binary floats.
    rows = deepcopy(SAMPLES[DatasetType.NERACA_HARIAN])
    rows[0]["saldo"] = 0.1
    result = load_xlsx("bad.xlsx", workbook_bytes(DatasetType.NERACA_HARIAN, rows))
    assert result.source is not None and result.findings
    assert result.findings[0].field == "saldo"


def test_row_with_unmasked_id_fails_and_no_value_leaked() -> None:
    rows = deepcopy(SAMPLES[DatasetType.GIRO_TABUNGAN])
    rows[0]["account_id"] = "PERSONAL-IDENTIFIER-12345"
    result = load_xlsx("bad.xlsx", workbook_bytes(DatasetType.GIRO_TABUNGAN, rows))
    assert result.findings and result.findings[0].field == "account_id"
    assert "PERSONAL-IDENTIFIER" not in str(result.findings)


def test_invalid_akad_is_failed() -> None:
    rows = deepcopy(SAMPLES[DatasetType.GIRO_TABUNGAN])
    rows[0]["akad"] = "INVALID"
    result = load_xlsx("bad.xlsx", workbook_bytes(DatasetType.GIRO_TABUNGAN, rows))
    assert result.findings[0].rule_id == "DQ-AKAD-001"


def test_metadata_missing_rejected() -> None:
    payload = workbook_bytes(DatasetType.NERACA_HARIAN)
    bad = mutate(payload, lambda wb: setattr(wb["__meta__"]["A2"], "value", "invalid_key"))
    assert load_xlsx("bad.xlsx", bad).source is None


def test_external_links_rejected_on_archive_contents() -> None:
    payload = workbook_bytes(DatasetType.NERACA_HARIAN)
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(payload)) as src, zipfile.ZipFile(out, "w") as dst:
        for item in src.infolist():
            dst.writestr(item, src.read(item.filename))
        dst.writestr("xl/externalLinks/externalLink1.xml", b"<unsafe />")
    assert load_xlsx("bad.xlsx", out.getvalue()).source is None
