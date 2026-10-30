"""Version 1.0 Fase-1 source contracts. Controls: R10, DQ-SCHEMA, DQ-AKAD.

Legal basis: Bank-approved data contract pending mobilization; no regulatory
factor or product-to-akad mapping is defined or implicitly accepted here.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, ClassVar, Literal

from pydantic import (
    AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field, StrictBool,
    field_validator, model_validator,
)

from lrm_engine.common.decimal_math import as_decimal


class DatasetType(StrEnum):
    NERACA_HARIAN = "NeracaHarian"
    PENEMPATAN_BI = "PenempatanBI"
    SURAT_BERHARGA_SYARIAH = "SuratBerhargaSyariah"
    PENEMPATAN_BANK_LAIN = "PenempatanBankLain"
    GIRO_TABUNGAN = "GiroTabungan"
    DEPOSITO = "Deposito"
    KEWAJIBAN_ANTARBANK = "KewajibanAntarBank"
    PEMBIAYAAN = "Pembiayaan"
    KONTINJENSI = "Kontinjensi"
    DISTRIBUSI_BAGI_HASIL = "DistribusiBagiHasil"
    BENCHMARK_IMBAL_HASIL = "BenchmarkImbalHasil"
    PERMODALAN = "Permodalan"
    KEWAJIBAN_GWM_PLM = "KewajibanGWMPLM"


# This is an initial data vocabulary, NOT the approved WP2 product/akad mapping.
class Akad(StrEnum):
    WADIAH = "wadiah"
    MUDHARABAH = "mudharabah"
    MUSYARAKAH = "musyarakah"
    MURABAHAH = "murabahah"
    IJARAH = "ijarah"
    IMBT = "imbt"
    QARDH = "qardh"
    ISTISHNA = "istishna"
    KAFALAH = "kafalah"
    WAKALAH = "wakalah"
    OTHER_PENDING_BANK_APPROVAL = "other_pending_bank_approval"


class Segment(StrEnum):
    PERORANGAN = "perorangan"
    UMK = "umk"
    KORPORASI = "korporasi"
    PEMERINTAH = "pemerintah"
    LEMBAGA_KEUANGAN = "lembaga_keuangan"
    OTHER_PENDING_BANK_APPROVAL = "other_pending_bank_approval"


def parse_exact_decimal(value: Any) -> Decimal:
    """Disallow binary float at every ingestion layer, including Excel numeric cells."""
    try:
        return as_decimal(value)
    except TypeError as exc:
        raise ValueError("Binary floating point or non-decimal numeric input forbidden") from exc


ExactDecimal = Annotated[Decimal, BeforeValidator(parse_exact_decimal)]
Nonnegative = Annotated[ExactDecimal, Field(ge=Decimal("0"))]
Fraction = Annotated[ExactDecimal, Field(ge=Decimal("0"), le=Decimal("1"))]
Positive = Annotated[ExactDecimal, Field(gt=Decimal("0"))]
Code = Annotated[str, Field(min_length=1, max_length=100)]
MaskedCode = Annotated[str, Field(pattern=r"^(?:MASK|TOKEN)-[A-Za-z0-9_-]{6,64}$")]
ISOCode = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]


class StrictRecord(BaseModel):
    currency: ISOCode  # row-level currency, independent of file reporting currency
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    # Used by DQ for a non-sensitive, deterministic duplicate identifier.
    unique_key: ClassVar[str]

    @field_validator("*", mode="before")
    @classmethod
    def normalize_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value


class SourceMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"]
    dataset_type: DatasetType
    reporting_date: date
    reporting_currency: ISOCode
    source_system: Code
    extracted_at: AwareDatetime
    source_reference: Code

    @field_validator("reporting_date", mode="before")
    @classmethod
    def date_only(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            raise ValueError("reporting_date must not include a time component")
        return value


class NeracaHarian(StrictRecord):
    unique_key: ClassVar[str] = "gl_code"
    gl_code: Code
    pos_neraca: Code
    saldo: ExactDecimal  # signed balances allowed on GL anchors


class PenempatanBI(StrictRecord):
    unique_key: ClassVar[str] = "placement_id"
    placement_id: Code
    jenis: Code  # GWM/FASBIS/SBIS etc, approved codebook pending
    gl_code: Code
    akad: Akad
    saldo: Nonnegative
    jatuh_tempo: date | None = None


class SuratBerhargaSyariah(StrictRecord):
    unique_key: ClassVar[str] = "instrument_id"
    instrument_id: Code
    gl_code: Code
    isin: Annotated[str, Field(pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")]
    jenis: Code
    issuer_code: Code
    akad: Akad
    rating: str | None = None
    agency: str | None = None
    jatuh_tempo: date
    nilai_pasar: Nonnegative
    encumbered_flag: StrictBool

    @model_validator(mode="after")
    def rating_pair(self) -> "SuratBerhargaSyariah":
        if bool(self.rating) != bool(self.agency):
            raise ValueError("rating and agency must both be populated or both be empty")
        return self


class PenempatanBankLain(StrictRecord):
    unique_key: ClassVar[str] = "placement_id"
    placement_id: Code
    gl_code: Code
    counterparty_code: Code
    akad: Akad
    jatuh_tempo: date
    saldo: Nonnegative


class GiroTabungan(StrictRecord):
    unique_key: ClassVar[str] = "account_id"
    account_id: MaskedCode
    gl_code: Code
    product_code: Code
    akad: Akad
    segmen: Segment
    lps_eligible: StrictBool
    operational_flag: StrictBool
    relationship_months: Annotated[int, Field(ge=0)]
    saldo: Nonnegative


class Deposito(StrictRecord):
    unique_key: ClassVar[str] = "account_id"
    account_id: MaskedCode
    gl_code: Code
    product_code: Code
    akad: Akad
    jatuh_tempo: date
    aro_flag: StrictBool
    early_withdrawal_penalty: Nonnegative | None = None
    segmen: Segment
    saldo: Nonnegative


class KewajibanAntarBank(StrictRecord):
    unique_key: ClassVar[str] = "funding_id"
    funding_id: Code
    gl_code: Code
    counterparty_code: Code
    akad: Akad
    jatuh_tempo: date
    saldo: Nonnegative


class Instalment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tanggal: date
    nilai: Positive


class Pembiayaan(StrictRecord):
    unique_key: ClassVar[str] = "facility_id"
    facility_id: MaskedCode
    gl_code: Code
    product_code: Code
    akad: Akad
    kolektibilitas: Annotated[int, Field(ge=1, le=5)]
    jatuh_tempo: date
    jadwal_angsuran: tuple[Instalment, ...]
    outstanding: Nonnegative
    encumbered_flag: StrictBool

    @field_validator("jadwal_angsuran", mode="before")
    @classmethod
    def parse_schedule(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        try:
            result = json.loads(value, parse_float=Decimal)
        except (ValueError, TypeError) as exc:
            raise ValueError("jadwal_angsuran must contain valid JSON") from exc
        if not isinstance(result, list):
            raise ValueError("jadwal_angsuran must be a JSON array")
        return result


class Kontinjensi(StrictRecord):
    unique_key: ClassVar[str] = "commitment_id"
    commitment_id: Code
    gl_code: Code | None = None  # off-balance sheet often has no GL anchor
    jenis: Code
    counterparty_type: Code
    akad: Akad
    nilai: Nonnegative


class DistribusiBagiHasil(StrictRecord):
    unique_key: ClassVar[str] = "distribution_id"
    distribution_id: Code
    product_code: Code
    akad: Akad
    tenor_months: Annotated[int, Field(ge=0)]
    nisbah_nasabah: Fraction  # decimal fraction, NOT percent: 0.6 == 60%
    distributable_revenue: Nonnegative
    equivalent_rate: ExactDecimal  # decimal fraction, negative rates not precluded


class BenchmarkImbalHasil(StrictRecord):
    unique_key: ClassVar[str] = "benchmark_type"
    benchmark_type: Code
    rate: ExactDecimal  # decimal fraction, may be negative
    sumber: Code
    tanggal_efektif: date


class Permodalan(StrictRecord):
    unique_key: ClassVar[str] = "component_id"
    component_id: Code
    gl_code: Code
    komponen_modal: Code
    nominal: Nonnegative


class KewajibanGWMPLM(StrictRecord):
    unique_key: ClassVar[str] = "reference_id"
    reference_id: Code
    rasio_gwm: Fraction
    rasio_plm: Fraction
    tanggal_efektif: date
    sumber: Code
    legal_basis: Code
    verification_status: Literal["DRAFT_UNVERIFIED"]


RecordClass = type[StrictRecord]
DATASET_MODELS: dict[DatasetType, RecordClass] = {
    DatasetType.NERACA_HARIAN: NeracaHarian,
    DatasetType.PENEMPATAN_BI: PenempatanBI,
    DatasetType.SURAT_BERHARGA_SYARIAH: SuratBerhargaSyariah,
    DatasetType.PENEMPATAN_BANK_LAIN: PenempatanBankLain,
    DatasetType.GIRO_TABUNGAN: GiroTabungan,
    DatasetType.DEPOSITO: Deposito,
    DatasetType.KEWAJIBAN_ANTARBANK: KewajibanAntarBank,
    DatasetType.PEMBIAYAAN: Pembiayaan,
    DatasetType.KONTINJENSI: Kontinjensi,
    DatasetType.DISTRIBUSI_BAGI_HASIL: DistribusiBagiHasil,
    DatasetType.BENCHMARK_IMBAL_HASIL: BenchmarkImbalHasil,
    DatasetType.PERMODALAN: Permodalan,
    DatasetType.KEWAJIBAN_GWM_PLM: KewajibanGWMPLM,
}


def expected_columns(dataset_type: DatasetType) -> tuple[str, ...]:
    return tuple(DATASET_MODELS[dataset_type].model_fields.keys())
