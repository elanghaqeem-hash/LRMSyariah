"""Issue #4 immutable DQ/GL lineage evidence bound to a WP3 LCR CalculationRun.

Trusted service only. SQLite triggers are test doubles; on-prem PostgreSQL
requires migration 0003, restricted role and Bank-signed source evidence vault.
"""
from __future__ import annotations

import hashlib
import json
import re
from uuid import uuid4
from typing import Any

from sqlalchemy import CheckConstraint, DDL, ForeignKey, String, Text, event, text
from sqlalchemy.orm import Mapped, Session, mapped_column

from lrm_engine.common.canonical import canonical_json
from lrm_services.models import Base, Principal
from lrm_services.runs import CalculationRun, RunError, RunService

SHA64 = re.compile(r"[0-9a-f]{64}\Z")


class LCRRunEvidence(Base):
    """One immutable evidence pack per run; stores only hashed file refs and GL aggregates."""

    __tablename__ = "lrm_lcr_run_evidence"
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("lrm_calculation_run.id"), primary_key=True)
    maker_id: Mapped[str] = mapped_column(String(180), ForeignKey("lrm_principal.subject"), nullable=False)
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parameter_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (
        CheckConstraint("length(evidence_sha256)=64", name="ck_lcr_evidence_sha"),
    )


class LCRReconCase(Base):
    """Failed variance case; checker decision records disposition, never overrides PASS."""

    __tablename__ = "lrm_lcr_recon_case"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("lrm_calculation_run.id"), nullable=False)
    gl_code: Mapped[str] = mapped_column(String(100), nullable=False)
    variance_json: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(12), nullable=False, default="HIGH")
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="OPEN")
    checker_id: Mapped[str | None] = mapped_column(String(180), ForeignKey("lrm_principal.subject"))
    checker_comment: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        CheckConstraint("status in ('OPEN','REVIEWED')", name="ck_lcr_case_status"),
        CheckConstraint("severity in ('HIGH','CRITICAL')", name="ck_lcr_case_severity"),
    )


for op in ("UPDATE", "DELETE"):
    event.listen(LCRRunEvidence.__table__, "after_create", DDL(
       f"CREATE TRIGGER lcr_evidence_{op.lower()}_blocked BEFORE {op} "
       "ON lrm_lcr_run_evidence BEGIN SELECT RAISE(ABORT, 'LCR evidence immutable'); END"
    ).execute_if(dialect="sqlite"))
    event.listen(LCRReconCase.__table__, "after_create", DDL(
       f"CREATE TRIGGER lcr_case_{op.lower()}_reviewed_blocked BEFORE {op} "
       "ON lrm_lcr_recon_case WHEN OLD.status='REVIEWED' "
       "BEGIN SELECT RAISE(ABORT, 'reviewed exception immutable'); END"
    ).execute_if(dialect="sqlite"))


def _hash(blob: str) -> str:
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _canonical_json(proof: dict[str, Any]) -> str:
    return canonical_json(proof).decode("utf-8")


def attach_lcr_proof(session: Session, maker_subject: str, run: CalculationRun,
                     proof: dict[str, Any]) -> LCRRunEvidence:
    principal = session.get(Principal, maker_subject)
    if (principal is None or not principal.enabled or principal.role != "MAKER" or
        run.maker_id != maker_subject or run.status != "DRAFT" or
        run.run_type not in ("LCR_DAILY", "LCR_MONTHLY")):
        raise PermissionError("Evidence attaches only to maker-owned draft LCR")
    blob = _canonical_json(proof)
    if not isinstance(proof.get("dq"), dict) or not isinstance(proof.get("recon"), dict):
        raise RunError("Typed data quality and recon evidence required")
    source = proof.get("source_file_sha256", {})
    from lrm_data.schema import DatasetType
    if (not isinstance(source, dict) or set(source) != {x.value for x in DatasetType}
            or not all(isinstance(v, str) and SHA64.fullmatch(v) for v in source.values())):
        raise RunError("Hash proof from all 13 sources is required")
    if proof.get("reporting_date") != run.reporting_date:
        raise RunError("Evidence date mismatch")
    if not SHA64.fullmatch(str(proof.get("mapping_sha256", ""))):
        raise RunError("Approved mapping fingerprint required")
    if proof.get("mapping_sha256") != run.akad_mapping_version:
        raise RunError("Run-to-mapping fingerprint mismatch")
    if proof.get("parameter_set_hash") != run.parameter_set_version:
        raise RunError("Run-to-parameter fingerprint mismatch")
    record = LCRRunEvidence(run_id=run.id, maker_id=maker_subject,
         input_sha256=run.input_sha256, parameter_sha256=run.parameter_sha256,
         evidence_sha256=_hash(blob), evidence_json=blob)
    session.add(record)
    session.flush()
    for line in proof["recon"].get("lines", []):
        if line["status"] != "PASS":
            case = LCRReconCase(run_id=run.id, gl_code=line["gl_code"],
                  variance_json=_canonical_json({"source_variance": line["source_variance"],
                         "engine_variance": line["engine_variance"]}),
                  severity="HIGH")
            session.add(case)
    session.flush()
    # Anchor evidence hash in the existing append-only WP3 AuditEvent chain.
    RunService(session, maker_subject)._audit("LCR_EVIDENCE_ATTACHED", run.id,
                       {"evidence_sha256": record.evidence_sha256})
    return record


def verify_lcr_proof(session: Session, run: CalculationRun) -> str:
    """Called at both validation and approval, disallowing boolean bypass."""
    proof = session.get(LCRRunEvidence, run.id)
    if proof is None or proof.maker_id != run.maker_id:
        raise RunError("LCR calculation has no independently anchored DQ/GL evidence")
    if proof.input_sha256 != run.input_sha256 or proof.parameter_sha256 != run.parameter_sha256:
        raise RunError("LCR evidence does not match frozen calculation snapshots")
    if _hash(proof.evidence_json) != proof.evidence_sha256:
        raise RunError("LCR evidence integrity hash mismatch")
    try:
        p = json.loads(proof.evidence_json)
    except ValueError as exc:
        raise RunError("Invalid LCR evidence document") from exc
    if _canonical_json(p) != proof.evidence_json:
        raise RunError("Noncanonical LCR evidence snapshot")
    if p["dq"]["status"] != "PASS" or p["recon"]["status"] != "PASS":
        raise RunError("LCR requires genuine DQ PASS and GL reconciliation PASS")
    if p["dq"]["checked_files"] != 13 or p["recon"]["date"] != run.reporting_date.isoformat():
        raise RunError("LCR source coverage/date does not match calculation run")
    if any(line["status"] != "PASS" for line in p["recon"].get("lines", [])):
        raise RunError("One or more LCR reconciliation lines failed")
    if not p["recon"].get("lines"):
        raise RunError("No GL reconciliation lines found")
    if p.get("parameter_set_hash") != run.parameter_set_version or p.get("mapping_sha256") != run.akad_mapping_version:
        raise RunError("LCR parameter/mapping provenance mismatch")
    return proof.evidence_sha256


def review_reconciliation_case(session: Session, checker_subject: str,
                               case_id: str, explanation: str) -> LCRReconCase:
    """Checker can acknowledge a failed GL; no waiver to approve failed runs."""
    actor = session.get(Principal, checker_subject)
    case = session.get(LCRReconCase, case_id)
    if actor is None or actor.role != "CHECKER" or not actor.enabled:
        raise PermissionError("Only enabled checker may review GL exceptions")
    if case is None or case.status != "OPEN" or not explanation.strip():
        raise RunError("Open recon case and explanation required")
    run = session.get(CalculationRun, case.run_id)
    if run is None or run.maker_id == checker_subject:
        raise PermissionError("Maker cannot independently review own GL variance")
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        session.execute(text("SELECT set_config('lrm.actor_id', :subject, true)"), {"subject": checker_subject})
    case.checker_id = checker_subject
    case.checker_comment = explanation.strip()
    case.status = "REVIEWED"
    session.flush()
    RunService(session, checker_subject)._audit("LCR_RECON_REVIEWED", run.id,
        {"case_id": case.id, "gl_code": case.gl_code})
    return case