"""Issue #4: evidence-bound source -> approved akad -> LCR -> GL reconciliation.

No regulatory coefficient, classification, FX rate or GL sign is inferred.
Only Bank-governed effective revisions are accepted; this is not a regulatory
model certification. Excel raw bytes are never logged or embedded in run snapshots.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Mapping, Sequence

from lrm_data.loader import LoadedSource
from lrm_data.reconciliation import ReconEntry, ReconPolicy, ReconReport, reconcile_three_layers
from lrm_data.schema import DatasetType
from lrm_engine.common.canonical import sha256_canonical
from lrm_engine.common.decimal_math import as_decimal
from lrm_services.akad_gateway import SOURCE_KEY_FIELDS, validate_batch_with_mapping
from lrm_services.governance import GovernanceService

# Dataset-specific business interpretation belongs to the data contract. It is
# deliberately separate from the regulatory mapping controlled by Bank/DPS.
POSITION_FIELD: dict[DatasetType, str] = {
    DatasetType.PENEMPATAN_BI: "saldo",
    DatasetType.SURAT_BERHARGA_SYARIAH: "nilai_pasar",
    DatasetType.PENEMPATAN_BANK_LAIN: "saldo",
    DatasetType.GIRO_TABUNGAN: "saldo",
    DatasetType.DEPOSITO: "saldo",
    DatasetType.KEWAJIBAN_ANTARBANK: "saldo",
    DatasetType.PEMBIAYAAN: "outstanding",
    DatasetType.KONTINJENSI: "nilai",
}
HQLA_DATASETS = frozenset({DatasetType.PENEMPATAN_BI, DatasetType.SURAT_BERHARGA_SYARIAH})
INFLOW_DATASETS = frozenset({DatasetType.PENEMPATAN_BANK_LAIN, DatasetType.PEMBIAYAAN, DatasetType.PENEMPATAN_BI})
OUTFLOW_DATASETS = frozenset({DatasetType.GIRO_TABUNGAN, DatasetType.DEPOSITO,
                              DatasetType.KEWAJIBAN_ANTARBANK, DatasetType.KONTINJENSI})
CAP_KEYS = ("hqlacap.level2", "hqlacap.level2b", "inflow.cap")


class LCRGateError(ValueError):
    """Only non-sensitive rule summaries may appear in messages."""


@dataclass(frozen=True)
class LCRSourcePolicy:
    """External signed policy: explicit reporting scope/sign and unwind declaration.

    gl_signs expresses how a detail positive balance compares to signed bank GL:
    +1 or -1. It is never inferred from akad/asset-liability labels.
    Each included GL must appear in both source and GL anchor. Other bank GLs
    are *outside* this Bank-approved LCR scope, not silently considered covered.
    """

    gl_signs: Mapping[str, int]
    scope_approval_ref: str
    scope_document_sha256: str
    has_unwind_transactions: bool
    unwind_review_ref: str
    recon_policy: ReconPolicy

    def __post_init__(self) -> None:
        from lrm_engine.lcr.calculator import HASH64
        if not self.gl_signs or not all(k.strip() and type(v) is int and v in (-1, 1)
                                            for k, v in self.gl_signs.items()):
            raise LCRGateError("Explicit signed GL coverage must be Bank-approved")
        if (not self.scope_approval_ref.strip() or not self.unwind_review_ref.strip()
                or not HASH64.fullmatch(self.scope_document_sha256)):
            raise LCRGateError("GL scope and unwind review require source evidence")
        if self.has_unwind_transactions:
            raise LCRGateError("Adjusted-unwind treatment not certified; block LCR run")


@dataclass(frozen=True)
class PreparedLCR:
    reporting_date: date
    input_snapshot: dict[str, object]
    parameter_snapshot: dict[str, object]
    data_quality: dict[str, object]
    reconciliation: dict[str, object]
    evidence: dict[str, object]
    mapping_hash: str
    source_hashes: dict[str, str]


def _category(value: str) -> tuple[str, str | None, str | None]:
    """Approved WP2 mapping format: EXCLUDE or HQLA:L1:factor, OUTFLOW:factor etc.

    Syntax is a *configuration contract*, not implicit sharia categorisation.
    """
    parts = value.split(":")
    if parts == ["EXCLUDE"]:
        return "EXCLUDE", None, None
    if len(parts) == 3 and parts[0] == "HQLA" and parts[1] in ("L1", "L2A", "L2B") and parts[2]:
        return "HQLA", parts[1], parts[2]
    if len(parts) == 2 and parts[0] in ("OUTFLOW", "INFLOW") and parts[1]:
        return parts[0], None, parts[1]
    raise LCRGateError("Unrecognized approved LCR category format")


def _amount(dataset: DatasetType, record: object, cutoff: date) -> Decimal:
    if dataset is DatasetType.PEMBIAYAAN:
        # Only contractual instalments due within 30 calendar days are input
        # cash flows. Outstanding remains the independent GL recon base.
        maturity = cutoff + timedelta(days=30)
        return sum((inst.nilai for inst in record.jadwal_angsuran  # type: ignore[attr-defined]
                    if cutoff < inst.tanggal <= maturity), Decimal(0))
    if dataset in (DatasetType.PENEMPATAN_BANK_LAIN, DatasetType.DEPOSITO,
                   DatasetType.KEWAJIBAN_ANTARBANK):
        if record.jatuh_tempo > cutoff + timedelta(days=30):  # type: ignore[attr-defined]
            return Decimal(0)
    return as_decimal(getattr(record, POSITION_FIELD[dataset]))


def _trace_records(sources: Sequence[LoadedSource], governance: GovernanceService,
                   cutoff: date) -> tuple[list[dict[str, object]], dict[str, str], set[str], list[ReconEntry],
                                          list[ReconEntry], dict[str, object]]:
    rows: list[dict[str, object]] = []
    source_hashes: dict[str, str] = {}
    factors: set[str] = set(CAP_KEYS)
    details: list[ReconEntry] = []
    engine_gross: list[ReconEntry] = []
    mapping_proofs: dict[str, object] = {}
    for source in sources:
        dataset = source.metadata.dataset_type
        source_hashes[dataset.value] = source.file_hash
        key_field = SOURCE_KEY_FIELDS.get(dataset)
        if key_field is None:
            continue
        for item in source.rows:
            record = item.record
            key = str(getattr(record, key_field))
            revision = governance.resolve("MAPPING", f"{dataset.value}|{key}", cutoff)
            mapping = governance.mapping(dataset.value, key, cutoff)
            if revision is None or mapping is None:
                raise LCRGateError("Missing effective approved mapping")
            from lrm_engine.akad.classifier import classify, MappingNotFound
            try:
                lcr_category, rule_id, version = classify(dataset=dataset.value,
                    source_key=key, akad=record.akad.value, as_of=cutoff, mapping=mapping)  # type: ignore[attr-defined]
            except MappingNotFound as exc:
                raise LCRGateError("Akad does not match approved source mapping") from exc
            group, level, factor_id = _category(lcr_category)
            if group == "HQLA" and dataset not in HQLA_DATASETS:
                raise LCRGateError("HQLA category not allowed for this source contract")
            if group == "INFLOW" and dataset not in INFLOW_DATASETS:
                raise LCRGateError("Inflow category not allowed for this source contract")
            if group == "OUTFLOW" and dataset not in OUTFLOW_DATASETS:
                raise LCRGateError("Outflow category not allowed for this source contract")
            if group != "EXCLUDE" and dataset not in POSITION_FIELD:
                raise LCRGateError("Nonposition dataset may only be EXCLUDE")
            if group == "HQLA" and getattr(record, "encumbered_flag", False):
                raise LCRGateError("Encumbered assets cannot enter HQLA")
            if factor_id is not None:
                factors.add(factor_id)
            mapping_proofs[f"{dataset.value}:{item.excel_row}"] = {
                "revision_id": revision.id, "version": version, "rule_id": rule_id,
                "syariah_ref": revision.syariah_review_ref or "",
                "legal_basis": revision.legal_basis,
            }
            if dataset in POSITION_FIELD:
                gross = as_decimal(getattr(record, POSITION_FIELD[dataset]))
                gl_code = getattr(record, "gl_code", None)
                if gl_code:
                    details.append(ReconEntry(gl_code, gross, cutoff.isoformat()))
                    engine_gross.append(ReconEntry(gl_code, gross, cutoff.isoformat()))
                if group != "EXCLUDE":
                    effective = _amount(dataset, record, cutoff)
                    if effective > 0:
                        rows.append({"kind": group, "level": level, "amount": effective,
                                     "factor_key": factor_id, "akad": record.akad.value,  # type: ignore[attr-defined]
                                     "rule_id": rule_id, "source_sha256": source.file_hash})
    return rows, source_hashes, factors, details, engine_gross, mapping_proofs


def _lcr_calculator(inputs: dict[str, object], params: dict[str, object]) -> dict[str, object]:
    """WP3 reproducible adapter; all arithmetic delegated to pure WP4 engine."""
    from lrm_engine.lcr.calculator import Factor, HQLALeg, RegulatoryLeg, calculate_lcr
    factors = {k: Factor(value=as_decimal(v["value"]), rule_id=v["rule_id"],
                         legal_basis=v["legal_basis"], approved_revision=v["approved_revision"],
                         verification_ref=v["verification_ref"])  # type: ignore[index]
               for k, v in params["factors"].items()}  # type: ignore[union-attr]
    hqla: list[HQLALeg] = []
    out: list[RegulatoryLeg] = []
    incoming: list[RegulatoryLeg] = []
    for item in inputs["legs"]:  # type: ignore[union-attr]
        common = dict(amount=as_decimal(item["amount"]), akad=item["akad"],
                      rule_id=item["rule_id"], source_sha256=item["source_sha256"],
                      factor_key=item["factor_key"])
        if item["kind"] == "HQLA":
            hqla.append(HQLALeg(level=item["level"], **common))
        elif item["kind"] == "OUTFLOW":
            out.append(RegulatoryLeg(**common))
        elif item["kind"] == "INFLOW":
            incoming.append(RegulatoryLeg(**common))
        else:
            raise LCRGateError("Unexpected LCR leg category")
    result = calculate_lcr(hqla=hqla, outflows=out, inflows=incoming,
                           factors=factors, has_unwind_transactions=inputs["has_unwind_transactions"])  # type: ignore[arg-type]
    return asdict(result)


def prepare_lcr(*, files: Mapping[str, bytes], governance: GovernanceService,
                reporting_date: date, reporting_currency: str,
                source_policy: LCRSourcePolicy) -> PreparedLCR:
    """13-file DQ + WP2 approved classifications + WP2 factors + three-layer GL.

    No magic defaults; missing datasets, categories, factors and GL fail closed.
    """
    # First read only the source metadata/fields. Regulatory parameter IDs are
    # derived exclusively from the approved mapping (never caller-provided).
    initial = validate_batch_with_mapping(files, service=governance,
       reporting_date=reporting_date, reporting_currency=reporting_currency,
       required_datasets=tuple(DatasetType), required_parameter_ids=list(CAP_KEYS))
    # DQ-PARAM-001 due to missing cap already blocks; do not rely on the caller.
    if initial.batch.report.status != "PASS":
        raise LCRGateError("13-source DQ, akad mapping, or mandatory cap parameter failed")
    legs, hashes, factor_ids, details, engine_base, mapping_info = _trace_records(
        initial.batch.sources, governance, reporting_date)
    if len(hashes) != len(DatasetType) or not legs:
        raise LCRGateError("Mandatory datasets or LCR classified positions missing")
    values, parameter_hash = governance.parameter_snapshot(sorted(factor_ids), reporting_date)
    factor_info: dict[str, dict[str, object]] = {}
    for key in sorted(factor_ids):
        rev = governance.resolve("PARAMETER", key, reporting_date)
        if rev is None or rev.verification_ref is None or rev.source_document_sha256 is None:
            raise LCRGateError("No independently approved factor evidence")
        value, unit, version = values[key]
        if unit.casefold() not in ("ratio", "fraction"):
            raise LCRGateError("Only approved fractional factors are accepted")
        factor_info[key] = {"value": value, "rule_id": key,
            "approved_revision": f"{rev.id}:v{version}", "legal_basis": rev.legal_basis,
            "verification_ref": rev.verification_ref, "source_document_sha256": rev.source_document_sha256}
    if set(source_policy.gl_signs) != {d.gl_code for d in details} or not details:
        raise LCRGateError("Approved GL scope does not match every balance-bearing LCR source")
    anchor = next(s for s in initial.batch.sources if s.metadata.dataset_type is DatasetType.NERACA_HARIAN)
    bank = [ReconEntry(x.record.gl_code, as_decimal(x.record.saldo), reporting_date.isoformat())
            for x in anchor.rows if x.record.gl_code in source_policy.gl_signs]
    signed_detail = [ReconEntry(x.gl_code, x.amount * source_policy.gl_signs[x.gl_code], x.reporting_date)
                     for x in details]
    signed_engine = [ReconEntry(x.gl_code, x.amount * source_policy.gl_signs[x.gl_code], x.reporting_date)
                     for x in engine_base]
    report: ReconReport = reconcile_three_layers(bank_gl=bank, source_detail=signed_detail,
                               engine_output=signed_engine, policy=source_policy.recon_policy)
    recon = {"status": report.status, "date": report.reporting_date,
             "parameter_version": report.parameter_version, "lines": [asdict(line) for line in report.lines]}
    dq = initial.batch.report.summary()
    mapping_hash = sha256_canonical(mapping_info)
    source_scope = {"gl_signs": dict(sorted(source_policy.gl_signs.items())),
                    "scope_approval_ref": source_policy.scope_approval_ref,
                    "scope_document_sha256": source_policy.scope_document_sha256,
                    "unwind_review_ref": source_policy.unwind_review_ref,
                    "reconciliation_policy": asdict(source_policy.recon_policy)}
    inputs: dict[str, object] = {"legs": legs, "has_unwind_transactions": False,
                                  "reporting_date": reporting_date, "reporting_currency": reporting_currency}
    params: dict[str, object] = {"factors": factor_info, "parameter_set_hash": parameter_hash}
    proof: dict[str, object] = {"status": "ENGINEERING_UNVERIFIED", "dq": dq,
         "recon": recon, "source_file_sha256": hashes,
         "mapping_sha256": mapping_hash, "scope": source_scope,
         "rule_ledger": mapping_info, "parameter_set_hash": parameter_hash,
         "reporting_date": reporting_date}
    return PreparedLCR(reporting_date, inputs, params, dq, recon, proof, mapping_hash, hashes)


def create_evidence_bound_lcr_run(*, session: object, maker_subject: str,
                     prepared: PreparedLCR, engine_version: str,
                     run_type: str = "LCR_DAILY") -> str:
    """Persist evidence before validating WP3; no caller can assert DQ/recon true.

    Failure to reconcile leaves an auditable DRAFT and exception register; it
    never turns into an approved/validated LCR until corrected in a new run.
    """
    from lrm_services.lcr_evidence import attach_lcr_proof
    from lrm_services.runs import RunService
    if run_type not in ("LCR_DAILY", "LCR_MONTHLY"):
        raise LCRGateError("Only controlled LCR run types accepted")
    svc = RunService(session, maker_subject)  # type: ignore[arg-type]
    run = svc.create(reporting_date=prepared.reporting_date, run_type=run_type,
                     engine_version=engine_version,
                     parameter_set_version=str(prepared.parameter_snapshot["parameter_set_hash"]),
                     akad_mapping_version=prepared.mapping_hash,
                     input_data=prepared.input_snapshot, parameters=prepared.parameter_snapshot)
    attach_lcr_proof(session, maker_subject, run, prepared.evidence)  # type: ignore[arg-type]
    if prepared.data_quality["status"] == "PASS" and prepared.reconciliation["status"] == "PASS":
        svc.validate(run.id, calculator=_lcr_calculator, dq_passed=True, reconciliation_passed=True)
    return run.id