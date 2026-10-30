"""UT-WP1-SCHEMA: exact Decimal, schema completeness, masked ID and akad."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

import pytest
from pydantic import ValidationError

from lrm_data.schema import (
    DATASET_MODELS, Akad, DatasetType, Deposito, GiroTabungan, NeracaHarian,
    Pembiayaan, SourceMetadata, expected_columns,
)
from scripts.generate_synthetic_inputs import SAMPLES


def test_thirteen_contracts_have_fields() -> None:
    assert len(DATASET_MODELS) == 13
    assert all(expected_columns(t) for t in DatasetType)


@pytest.mark.parametrize("dataset", list(DatasetType))
def test_every_synthetic_row_matches_schema(dataset: DatasetType) -> None:
    for values in SAMPLES[dataset]:
        record = DATASET_MODELS[dataset].model_validate(values)
        assert record is not None


def test_decimal_string_exact_and_binary_float_rejected() -> None:
    item = NeracaHarian.model_validate({"currency":"IDR", "gl_code":"GL", "pos_neraca":"saldo", "saldo":"0.10"})
    assert item.saldo == Decimal("0.10")
    with pytest.raises(ValidationError):
        NeracaHarian.model_validate({"currency":"IDR", "gl_code":"GL", "pos_neraca":"saldo", "saldo":0.1})
    with pytest.raises(ValidationError):
        NeracaHarian.model_validate({"currency":"IDR", "gl_code":"GL", "pos_neraca":"saldo", "saldo":"NaN"})


def test_unmasked_customer_id_blocked() -> None:
    record = dict(SAMPLES[DatasetType.GIRO_TABUNGAN][0], account_id="123456789010")
    with pytest.raises(ValidationError):
        GiroTabungan.model_validate(record)


def test_akad_vocabulary_is_provisional_not_a_mapping() -> None:
    record = dict(SAMPLES[DatasetType.DEPOSITO][0], akad="unknown")
    with pytest.raises(ValidationError):
        Deposito.model_validate(record)
    assert Akad.OTHER_PENDING_BANK_APPROVAL.value == "other_pending_bank_approval"


def test_json_instalments_are_exact_decimal() -> None:
    sample = deepcopy(SAMPLES[DatasetType.PEMBIAYAAN][0])
    sample["jadwal_angsuran"] = '[{"tanggal":"2026-11-02", "nilai":0.11}]'
    record = Pembiayaan.model_validate(sample)
    assert record.jadwal_angsuran[0].nilai == Decimal("0.11")


def test_extra_field_rejected() -> None:
    record = dict(SAMPLES[DatasetType.NERACA_HARIAN][0], confidential_field="x")
    with pytest.raises(ValidationError):
        NeracaHarian.model_validate(record)


def test_invalid_ratio_rejected() -> None:
    record = dict(SAMPLES[DatasetType.DISTRIBUSI_BAGI_HASIL][0], nisbah_nasabah="1.2")
    with pytest.raises(ValidationError):
        DATASET_MODELS[DatasetType.DISTRIBUSI_BAGI_HASIL].model_validate(record)


def test_timezone_required() -> None:
    from scripts.generate_synthetic_inputs import META
    with pytest.raises(ValidationError):
        SourceMetadata.model_validate(dict(META, dataset_type="NeracaHarian",
                                           extracted_at="2026-10-30T01:00:00"))
