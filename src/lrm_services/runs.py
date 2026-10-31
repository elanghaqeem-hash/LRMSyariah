"""WP3 controlled calculation runs and append-only audit ledger.

ENG-TRACE-001 / R13 / R16: engineering governance, not a regulatory factor.
Only authenticated service principals should reach this boundary. PG DB controls
must run with a restricted application role; DB owners can disable triggers.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from typing import Any, Callable
from uuid import uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, DDL, ForeignKey, Integer, String, Text, UniqueConstraint, event, select, text
from sqlalchemy.orm import Mapped, Session, mapped_column

from lrm_engine.common.canonical import canonical_json, sha256_canonical
from lrm_services.models import Base, Principal, utc_now

SHA = re.compile(r"[0-9a-f]{64}\Z")
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+\+[0-9a-f]{7,40}\Z")
GENESIS = "0" * 64


class RunError(ValueError):
    """Privacy-safe control error; never embed customer source data."""


class CalculationRun(Base):
    """APPROVED rows are immutable; supersession points forward from a new row."""

    __tablename__ = "lrm_calculation_run"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    reporting_date: Mapped[date] = mapped_column(Date, nullable=False)
    run_type: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    maker_id: Mapped[str] = mapped_column(ForeignKey("lrm_principal.subject"), nullable=False)
    checker_id: Mapped[str | None] = mapped_column(ForeignKey("lrm_principal.subject"))
    engine_version: Mapped[str] = mapped_column(String(60), nullable=False)
    parameter_set_version: Mapped[str] = mapped_column(String(120), nullable=False)
    akad_mapping_version: Mapped[str] = mapped_column(String(120), nullable=False)
    scenario_id: Mapped[str | None] = mapped_column(String(120))
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parameter_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    input_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    parameter_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    result_snapshot: Mapped[str | None] = mapped_column(Text)
    result_sha256: Mapped[str | None] = mapped_column(String(64))
    dq_summary: Mapped[str | None] = mapped_column(Text)
    recon_summary: Mapped[str | None] = mapped_column(Text)
    supersedes_run_id: Mapped[str | None] = mapped_column(ForeignKey("lrm_calculation_run.id"))
    change_reason: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT','VALIDATED','SUBMITTED','APPROVED','REJECTED')", name="ck_run_status"),
        CheckConstraint("run_type IN ('LCR_DAILY','LCR_MONTHLY','NSFR_MONTHLY','NSFR_QUARTERLY','STRESS','SURVIVAL','DCR')", name="ck_run_type"),
        CheckConstraint("checker_id IS NULL OR checker_id <> maker_id", name="ck_run_four_eyes"),
        CheckConstraint("status <> 'APPROVED' OR (checker_id IS NOT NULL AND approved_at IS NOT NULL AND result_sha256 IS NOT NULL)", name="ck_run_approval"),
        CheckConstraint("supersedes_run_id IS NULL OR supersedes_run_id <> id", name="ck_no_self_supersession"),
        UniqueConstraint("supersedes_run_id", name="uq_run_supersession"),
    )


class AuditEvent(Base):
    """Append-only, globally ordered event ledger. Contains metadata, no PII."""

    __tablename__ = "lrm_audit_event"
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    occurred_at: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(180), nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    object_id: Mapped[str] = mapped_column(String(36), nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)


# SQLite is a TEST DOUBLE, not an acceptable on-prem production DB.
# Mirror immutable transitions for raw UPDATE/DELETE in the local test environment.
for model, prefix, body in (
    (CalculationRun, "calc", "WHEN OLD.status = 'APPROVED'"),
    (AuditEvent, "audit", ""),
):
    for operation in ("UPDATE", "DELETE"):
        trigger = f"lrm_no_{operation.lower()}_{prefix}"
        table = model.__tablename__
        sql = (f"CREATE TRIGGER {trigger} BEFORE {operation} ON {table} "
               f"{body} BEGIN SELECT RAISE(ABORT, 'immutable record'); END")
        event.listen(model.__table__, "after_create", DDL(sql).execute_if(dialect="sqlite"))


def _payload(event: AuditEvent) -> dict[str, Any]:
    return {"sequence": event.sequence, "occurred_at": event.occurred_at,
            "actor_id": event.actor_id, "event_type": event.event_type,
            "object_id": event.object_id, "metadata_json": event.metadata_json,
            "previous_hash": event.previous_hash}


def verify_ledger(session: Session) -> int:
    """Verify event order, complete sequence, canonical hash chain and genesis."""
    with session.no_autoflush:
        events = session.scalars(select(AuditEvent).order_by(AuditEvent.sequence)).all()
    previous = GENESIS
    for count, row in enumerate(events, 1):
        if row.sequence != count or row.previous_hash != previous:
            raise RunError("Audit ledger sequence/previous hash mismatch")
        if sha256_canonical(_payload(row)) != row.event_hash:
            raise RunError("Audit ledger event hash mismatch")
        previous = row.event_hash
    return len(events)


class RunService:
    """Transaction-bound service; commit after each operation in the caller."""

    def __init__(self, session: Session, subject: str):
        self.session = session
        actor = session.get(Principal, subject)
        if actor is None or not actor.enabled:
            raise PermissionError("Unknown or disabled principal")
        self.actor = actor
        if session.bind is not None and session.bind.dialect.name == "postgresql":
            session.execute(text("SELECT set_config('lrm.actor_id', :actor, true)"), {"actor": subject})

    def _require(self, role: str) -> None:
        if self.actor.role != role:
            raise PermissionError(f"Requires {role} role")
        if self.session.bind is not None and self.session.bind.dialect.name == "postgresql":
            self.session.execute(text("SELECT set_config('lrm.actor_id', :actor, true)"), {"actor": self.actor.subject})

    def _audit(self, action: str, run_id: str, metadata: dict[str, Any]) -> None:
        if self.session.bind is not None and self.session.bind.dialect.name == "postgresql":
            # Every writer serializes on this lock to prevent interleaving ledger tips.
            self.session.execute(text("SELECT pg_advisory_xact_lock(71204603)"))
        last = self.session.scalar(select(AuditEvent).order_by(AuditEvent.sequence.desc()).limit(1))
        event = AuditEvent(sequence=(last.sequence + 1 if last else 1),
                           occurred_at=utc_now().isoformat().replace("+00:00", "Z"), actor_id=self.actor.subject,
                           event_type=action, object_id=run_id,
                           metadata_json=canonical_json(metadata).decode("utf-8"),
                           previous_hash=last.event_hash if last else GENESIS,
                           event_hash="")
        event.event_hash = sha256_canonical(_payload(event))
        self.session.add(event)
        self.session.flush()

    def record_event(self, event_type: str, object_id: str, *, file_sha256: str | None = None) -> None:
        """Auditable metadata for upload/export/login/config; never log source rows."""
        allowed = {"UPLOAD", "EXPORT", "LOGIN", "LOGOUT", "LOGIN_FAILED",
                   "PARAMETER_CHANGED", "AKAD_MAPPING_CHANGED", "CONFIG_CHANGED"}
        if event_type not in allowed or not object_id.strip():
            raise RunError("Unsupported audit event type or object")
        if file_sha256 is not None and not SHA.fullmatch(file_sha256):
            raise RunError("Invalid evidence SHA-256")
        self._audit(event_type, object_id, {"file_sha256": file_sha256})

    def create(self, *, reporting_date: date, run_type: str,
               engine_version: str, parameter_set_version: str,
               akad_mapping_version: str, input_data: Any, parameters: Any,
               scenario_id: str | None = None, supersedes_run_id: str | None = None,
               change_reason: str | None = None) -> CalculationRun:
        self._require("MAKER")
        if not VERSION.fullmatch(engine_version):
            raise RunError("engine_version requires semver+git SHA")
        if not parameter_set_version.strip() or not akad_mapping_version.strip():
            raise RunError("Versioned parameters and akad mapping are required")
        inp = canonical_json(input_data).decode("utf-8")
        par = canonical_json(parameters).decode("utf-8")
        if supersedes_run_id:
            prior = self.session.get(CalculationRun, supersedes_run_id)
            if prior is None or prior.status != "APPROVED" or not change_reason:
                raise RunError("Supersession needs approved predecessor and reason")
            if prior.run_type != run_type or prior.reporting_date != reporting_date:
                raise RunError("Supersession must have matching type and reporting date")
        run = CalculationRun(reporting_date=reporting_date, run_type=run_type,
                 engine_version=engine_version, parameter_set_version=parameter_set_version,
                 akad_mapping_version=akad_mapping_version, scenario_id=scenario_id,
                 maker_id=self.actor.subject, input_sha256=hashlib.sha256(inp.encode()).hexdigest(),
                 parameter_sha256=hashlib.sha256(par.encode()).hexdigest(),
                 input_snapshot=inp, parameter_snapshot=par,
                 supersedes_run_id=supersedes_run_id, change_reason=change_reason)
        self.session.add(run)
        self.session.flush()
        self._audit("RUN_CREATED", run.id, {"input_sha256": run.input_sha256,
              "parameter_sha256": run.parameter_sha256, "run_type": run_type})
        return run

    def validate(self, run_id: str, *, calculator: Callable[[Any, Any], Any],
                 dq_passed: bool, reconciliation_passed: bool) -> CalculationRun:
        self._require("MAKER")
        run = self._get(run_id, "DRAFT")
        if run.maker_id != self.actor.subject or not dq_passed or not reconciliation_passed:
            raise RunError("Only original maker may validate after DQ and reconciliation PASS")
        if run.run_type in ("LCR_DAILY", "LCR_MONTHLY"):
            from lrm_services.lcr_evidence import verify_lcr_proof
            verify_lcr_proof(self.session, run)
        self._check_snapshots(run)
        # Calculation output contains only approved-modeled test data in current WP.
        result = calculator(json.loads(run.input_snapshot), json.loads(run.parameter_snapshot))
        result_json = canonical_json(result)
        run.result_snapshot = result_json.decode("utf-8")
        run.result_sha256 = hashlib.sha256(result_json).hexdigest()
        run.dq_summary = "PASS"
        run.recon_summary = "PASS"
        run.status = "VALIDATED"
        self.session.flush()
        self._audit("RUN_VALIDATED", run.id, {"result_sha256": run.result_sha256})
        return run

    def submit(self, run_id: str) -> CalculationRun:
        self._require("MAKER")
        run = self._get(run_id, "VALIDATED")
        if run.maker_id != self.actor.subject:
            raise RunError("Only original maker may submit")
        self._check_snapshots(run)
        run.status, run.submitted_at = "SUBMITTED", utc_now()
        self.session.flush()
        self._audit("RUN_SUBMITTED", run.id, {"result_sha256": run.result_sha256})
        return run

    def approve(self, run_id: str) -> CalculationRun:
        self._require("CHECKER")
        run = self._get(run_id, "SUBMITTED")
        if run.maker_id == self.actor.subject:
            raise PermissionError("Maker cannot approve own run")
        if run.run_type in ("LCR_DAILY", "LCR_MONTHLY"):
            from lrm_services.lcr_evidence import verify_lcr_proof
            verify_lcr_proof(self.session, run)
        self._check_snapshots(run)
        if run.dq_summary != "PASS" or run.recon_summary != "PASS" or not run.result_sha256:
            raise RunError("Cannot approve without DQ, recon and result")
        if hashlib.sha256(run.result_snapshot.encode()).hexdigest() != run.result_sha256:
            raise RunError("Result snapshot tampered")
        run.checker_id, run.approved_at, run.status = self.actor.subject, utc_now(), "APPROVED"
        self.session.flush()
        self._audit("RUN_APPROVED", run.id, {"result_sha256": run.result_sha256})
        return run

    def reject(self, run_id: str, reason: str) -> CalculationRun:
        self._require("CHECKER")
        run = self._get(run_id, "SUBMITTED")
        if not reason.strip():
            raise RunError("Rejection reason required")
        if run.maker_id == self.actor.subject:
            raise PermissionError("Maker cannot reject own run")
        run.status, run.rejected_at, run.rejection_reason = "REJECTED", utc_now(), reason.strip()
        run.checker_id = self.actor.subject
        self.session.flush()
        self._audit("RUN_REJECTED", run.id, {"reason_recorded": True})
        return run

    def reproduce(self, run_id: str, *, calculator: Callable[[Any, Any], Any],
                  engine_version: str) -> str:
        run = self.session.get(CalculationRun, run_id)
        if run is None or run.status != "APPROVED":
            raise RunError("Only approved runs can be reproduced")
        if engine_version != run.engine_version:
            raise RunError("Engine version mismatch; archived build is required")
        self._check_snapshots(run)
        result = canonical_json(calculator(json.loads(run.input_snapshot),
                                          json.loads(run.parameter_snapshot)))
        digest = hashlib.sha256(result).hexdigest()
        if digest != run.result_sha256:
            raise RunError("Reproduction hash mismatch")
        return digest

    @staticmethod
    def _check_snapshots(run: CalculationRun) -> None:
        if hashlib.sha256(run.input_snapshot.encode()).hexdigest() != run.input_sha256:
            raise RunError("Input snapshot hash mismatch")
        if hashlib.sha256(run.parameter_snapshot.encode()).hexdigest() != run.parameter_sha256:
            raise RunError("Parameter snapshot hash mismatch")
        # Verify canonical representation and reject hidden whitespace or JSON edits.
        for blob in (run.input_snapshot, run.parameter_snapshot):
            if canonical_json(json.loads(blob)).decode() != blob:
                raise RunError("Noncanonical calculation snapshot")

    def _get(self, run_id: str, expected: str) -> CalculationRun:
        run = self.session.get(CalculationRun, run_id)
        if run is None or run.status != expected:
            raise RunError(f"Run not in state {expected}")
        return run