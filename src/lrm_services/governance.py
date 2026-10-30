"""WP2 parameter and akad mapping approval service. R02, R06, R12, UT-PHASE.

All writes require Bank-IdP identity integration in WP6; tests use synthetic
principals only. Parameters are stored as canonical decimal strings, never float.
The service and database constraints both reject maker self-approval.
"""
from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from lrm_engine.common.canonical import canonical_json, sha256_canonical
from lrm_engine.common.decimal_math import as_decimal, decimal_plain
from lrm_services.models import GovernedRevision, Principal, utc_now

SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
KEY_PATTERN = re.compile(r"[A-Za-z0-9_.:|-]{1,260}\Z")
ROLE_MAKER = "MAKER"
ROLE_CHECKER = "CHECKER"


class GovernanceError(ValueError):
    """Safe error message; never include source amounts or personal IDs."""


def _required(value: str | None, *, field: str) -> str:
    if not value or not value.strip() or "[VERIFY]" in value.upper() or "TBD" in value.upper():
        raise GovernanceError(f"{field} must contain an approved non-placeholder reference")
    return value.strip()


def mapping_key(dataset: str, source_key: str) -> str:
    if "|" in dataset or "|" in source_key or not dataset or not source_key:
        raise GovernanceError("Invalid dataset and classifier key")
    return f"{dataset}|{source_key}"


class GovernanceService:
    """Authenticated service boundary: never trust a role claim supplied by the request.

    Caller supplies an authenticated OIDC subject; role is always read from DB.
    Production PostgreSQL constraints/triggers independently enforce SoD.
    """

    def __init__(self, session: Session, actor_subject: str):
        self.session = session
        actor = session.get(Principal, actor_subject)
        if actor is None or not actor.enabled:
            raise PermissionError("Unknown or disabled subject")
        self.actor = actor
        if session.bind is not None and session.bind.dialect.name == "postgresql":
            # Defense in depth: PG trigger obtains identity from the transaction.
            # Only the trusted backend DB role may set this; DB access must not be
            # exposed to end users. WP6 binds subject from verified IdP claims.
            session.execute(text("SELECT set_config('lrm.actor_id', :subject, true)"),
                            {"subject": actor_subject})

    def _require(self, role: str) -> None:
        # Refresh trusted transaction-local actor even if multiple service objects
        # share one SQLAlchemy session (important for the PostgreSQL DB trigger).
        if self.session.bind is not None and self.session.bind.dialect.name == "postgresql":
            self.session.execute(text("SELECT set_config('lrm.actor_id', :subject, true)"),
                                 {"subject": self.actor.subject})
        if self.actor.role != role:
            raise PermissionError(f"Only {role} may perform this operation")

    def _next_version(self, kind: str, key: str) -> int:
        versions = self.session.scalars(select(GovernedRevision.version).where(
            GovernedRevision.kind == kind, GovernedRevision.item_key == key)).all()
        return max(versions, default=0) + 1

    def _draft(self, kind: str, key: str, *, payload: dict[str, Any],
               effective_from: date, effective_to: date | None,
               legal_basis: str, change_reason: str, retirement: bool = False) -> GovernedRevision:
        self._require(ROLE_MAKER)
        if not KEY_PATTERN.fullmatch(key):
            raise GovernanceError("Invalid governed item key")
        if effective_to is not None and effective_to < effective_from:
            raise GovernanceError("Invalid effective-date interval")
        _required(change_reason, field="change_reason")
        if not legal_basis.strip():
            raise GovernanceError("legal_basis must be populated")
        record = GovernedRevision(
            kind=kind, item_key=key, version=self._next_version(kind, key),
            effective_from=effective_from, effective_to=effective_to,
            payload_json=canonical_json(payload).decode("utf-8"),
            legal_basis=legal_basis, change_reason=change_reason,
            maker_id=self.actor.subject, retirement=retirement,
            status="DRAFT_UNVERIFIED",
        )
        self.session.add(record)
        self.session.flush()
        return record

    def draft_parameter(self, *, param_id: str, value: Decimal | str | int | None,
                        unit: str, effective_from: date, effective_to: date | None = None,
                        legal_basis: str, change_reason: str) -> GovernedRevision:
        """Bank parameter remains DRAFT_UNVERIFIED until independent approval."""
        exact = None if value is None else decimal_plain(as_decimal(value))
        if not unit.strip():
            raise GovernanceError("Parameter unit is required")
        return self._draft("PARAMETER", param_id,
                           payload={"value": exact, "unit": unit.strip()},
                           effective_from=effective_from, effective_to=effective_to,
                           legal_basis=legal_basis, change_reason=change_reason)

    def draft_mapping(self, *, dataset: str, source_key: str, akad: str,
                      balance_side: str, lcr_category: str, nsfr_category: str,
                      rule_id: str, effective_from: date, effective_to: date | None = None,
                      legal_basis: str, change_reason: str) -> GovernedRevision:
        """Regulatory categories are explicitly provided by Bank, never inferred."""
        from lrm_data.schema import Akad, DatasetType
        if dataset not in {x.value for x in DatasetType} or dataset not in {
            "PenempatanBI", "SuratBerhargaSyariah", "PenempatanBankLain",
            "GiroTabungan", "Deposito", "KewajibanAntarBank", "Pembiayaan",
            "Kontinjensi", "DistribusiBagiHasil",
        }:
            raise GovernanceError("Dataset has no akad classification contract")
        if akad not in {x.value for x in Akad} or akad == "other_pending_bank_approval":
            raise GovernanceError("Only known, specific akad may be mapped")
        for label, value in (("source_key", source_key), ("balance_side", balance_side),
                             ("lcr_category", lcr_category), ("nsfr_category", nsfr_category),
                             ("rule_id", rule_id)):
            _required(value, field=label)
        return self._draft("MAPPING", mapping_key(dataset, source_key),
                           payload={"dataset": dataset, "source_key": source_key,
                                    "akad": akad, "balance_side": balance_side,
                                    "lcr_category": lcr_category,
                                    "nsfr_category": nsfr_category, "rule_id": rule_id},
                           effective_from=effective_from, effective_to=effective_to,
                           legal_basis=legal_basis, change_reason=change_reason)

    def draft_retirement(self, *, kind: str, item_key: str, effective_from: date,
                         change_reason: str, legal_basis: str) -> GovernedRevision:
        """Retire by a separately approved tombstone; do not alter historical active row."""
        if kind not in ("PARAMETER", "MAPPING"):
            raise GovernanceError("Unsupported object kind")
        if self.resolve(kind, item_key, effective_from) is None:
            raise GovernanceError("No active revision to retire on effective date")
        return self._draft(kind, item_key, payload={}, effective_from=effective_from,
                           effective_to=None, legal_basis=legal_basis,
                           change_reason=change_reason, retirement=True)

    def _locked(self, revision_id: str) -> GovernedRevision:
        record = self.session.scalar(select(GovernedRevision).where(
            GovernedRevision.id == revision_id).with_for_update())
        if record is None:
            raise GovernanceError("Unknown revision")
        return record

    def submit(self, revision_id: str) -> GovernedRevision:
        self._require(ROLE_MAKER)
        record = self._locked(revision_id)
        if record.maker_id != self.actor.subject or record.status != "DRAFT_UNVERIFIED":
            raise PermissionError("Maker may submit only own draft")
        if not record.retirement:
            payload = json.loads(record.payload_json)
            if record.kind == "PARAMETER" and payload["value"] is None:
                raise GovernanceError("Null parameter value may not be submitted")
        _required(record.legal_basis, field="legal_basis")
        record.status = "PENDING"
        record.submitted_at = utc_now()
        self.session.flush()
        return record

    def reject(self, revision_id: str, *, reason: str) -> GovernedRevision:
        self._require(ROLE_CHECKER)
        record = self._locked(revision_id)
        if record.status != "PENDING" or record.maker_id == self.actor.subject:
            raise GovernanceError("Only an independent checker may reject pending revisions")
        record.status = "DRAFT_UNVERIFIED"
        record.rejection_reason = _required(reason, field="rejection_reason")
        record.rejected_at = utc_now()
        record.rejected_by_id = self.actor.subject
        record.submitted_at = None
        self.session.flush()
        return record

    def approve(self, revision_id: str, *, source_document_sha256: str | None = None,
                verification_ref: str | None = None,
                syariah_review_ref: str | None = None) -> GovernedRevision:
        self._require(ROLE_CHECKER)
        record = self._locked(revision_id)
        if record.status != "PENDING" or record.submitted_at is None:
            raise GovernanceError("Only submitted pending versions may be approved")
        if record.maker_id == self.actor.subject:
            raise PermissionError("Maker self-approval is forbidden")
        # No approved revisions with the same effective start are permitted.
        existing = self.session.scalar(select(GovernedRevision.id).where(
            GovernedRevision.kind == record.kind,
            GovernedRevision.item_key == record.item_key,
            GovernedRevision.effective_from == record.effective_from,
            GovernedRevision.status.in_(("ACTIVE", "RETIRED"))))
        if existing is not None:
            raise GovernanceError("An approved version already starts on this date")
        max_prior_start = self.session.scalar(select(GovernedRevision.effective_from).where(
            GovernedRevision.kind == record.kind,
            GovernedRevision.item_key == record.item_key,
            GovernedRevision.status.in_(("ACTIVE", "RETIRED")))
            .order_by(GovernedRevision.effective_from.desc()).limit(1))
        if max_prior_start is not None and record.effective_from <= max_prior_start:
            raise GovernanceError("Backdated activation would alter previously approved history")
        if not record.retirement and record.kind == "PARAMETER":
            if not source_document_sha256 or not SHA256_PATTERN.fullmatch(source_document_sha256):
                raise GovernanceError("SHA-256 of verified regulatory source is required")
            checked_ref = _required(verification_ref, field="verification_ref")
            record.source_document_sha256 = source_document_sha256
            record.verification_ref = checked_ref
        if not record.retirement and record.kind == "MAPPING":
            checked_sharia_ref = _required(syariah_review_ref, field="syariah_review_ref")
            record.syariah_review_ref = checked_sharia_ref
        record.checker_id = self.actor.subject
        record.approved_at = utc_now()
        record.status = "RETIRED" if record.retirement else "ACTIVE"
        self.session.flush()
        return record

    def resolve(self, kind: str, item_key: str, as_of: date) -> GovernedRevision | None:
        """Resolve latest effective approved revision, including retirement tombstones.

        Date-effective revisions do not automatically reactivate older versions after
        a later revision expires. No ambiguous overlapping same-day approvals.
        """
        if kind not in ("PARAMETER", "MAPPING"):
            raise GovernanceError("Unsupported object kind")
        chosen = self.session.scalar(select(GovernedRevision).where(
            GovernedRevision.kind == kind, GovernedRevision.item_key == item_key,
            GovernedRevision.effective_from <= as_of,
            GovernedRevision.status.in_(("ACTIVE", "RETIRED")))
            .order_by(GovernedRevision.effective_from.desc(), GovernedRevision.version.desc())
            .limit(1))
        if (chosen is None or chosen.status == "RETIRED" or
            (chosen.effective_to is not None and chosen.effective_to < as_of)):
            return None
        return chosen

    def parameter(self, param_id: str, as_of: date) -> tuple[Decimal, str, int] | None:
        record = self.resolve("PARAMETER", param_id, as_of)
        if record is None:
            return None
        payload = json.loads(record.payload_json, parse_float=Decimal)
        if payload.get("value") is None:
            raise GovernanceError("Approved parameter has invalid null value")
        return as_decimal(payload["value"]), payload["unit"], record.version

    def mapping(self, dataset: str, source_key: str, as_of: date):
        """Build a pure-engine ApprovedMapping only from an active row."""
        from lrm_engine.akad.classifier import ApprovedMapping
        record = self.resolve("MAPPING", mapping_key(dataset, source_key), as_of)
        if record is None:
            return None
        payload = json.loads(record.payload_json)
        return ApprovedMapping(**payload, mapping_version=record.version,
                               effective_from=record.effective_from,
                               effective_to=record.effective_to,
                               syariah_review_ref=record.syariah_review_ref or "")

    def parameter_snapshot(self, ids: list[str], as_of: date) -> tuple[dict[str, tuple[Decimal, str, int]], str]:
        """Return complete approved parameter set and deterministic version fingerprint.

        Missing parameters fail closed. The returned hash can be pinned by WP3.
        The caller may not use an empty/duplicated required set to bypass checks.
        """
        if not ids or len(set(ids)) != len(ids):
            raise GovernanceError("An explicit non-empty unique parameter set is required")
        result: dict[str, tuple[Decimal, str, int]] = {}
        fingerprints: list[dict[str, str | int]] = []
        for key in sorted(ids):
            revision = self.resolve("PARAMETER", key, as_of)
            if revision is None:
                raise GovernanceError("Required parameter is not approved for reporting date")
            payload = json.loads(revision.payload_json)
            amount = as_decimal(payload["value"])
            result[key] = (amount, payload["unit"], revision.version)
            fingerprints.append({"id": key, "version": revision.version,
                                 "value": decimal_plain(amount), "unit": payload["unit"],
                                 "evidence_sha256": revision.source_document_sha256 or ""})
        return result, sha256_canonical({"as_of": as_of, "parameters": fingerprints})
