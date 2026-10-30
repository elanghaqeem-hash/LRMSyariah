"""WP2 persistent revision register; R02, R06, R12 and DQ-AKAD-004.

Legal basis: POJK 20/2025 [VERIFY exact clauses]; internal governance control.
No regulatory amounts or Islamic product categorisations are provided here.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint, event, text, DDL,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Principal(Base):
    """Identity subjects originate from Bank IdP in WP6; fixture identities only in WP2."""

    __tablename__ = "lrm_principal"
    subject: Mapped[str] = mapped_column(String(180), primary_key=True)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    __table_args__ = (
        CheckConstraint("role in ('MAKER','CHECKER','AUDITOR','ADMINISTRATOR','ALCO')",
                        name="ck_principal_role"),
    )


class GovernedRevision(Base):
    """Immutable when activated/retired; effective-time revisions override older revisions.

    A new approved revision takes precedence from its effective_from date. A retired
    (tombstone) revision discontinues the key, without deleting earlier history.
    Event logging and immutable calculation runs are the next WP (WP3).
    """

    __tablename__ = "lrm_governed_revision"
    id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                    default=lambda: str(uuid4()))
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # PARAMETER/MAPPING
    item_key: Mapped[str] = mapped_column(String(260), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(25), nullable=False,
                                        default="DRAFT_UNVERIFIED")
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)  # canonical JSON
    legal_basis: Mapped[str] = mapped_column(Text, nullable=False)
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)
    retirement: Mapped[bool] = mapped_column(nullable=False, default=False)
    maker_id: Mapped[str] = mapped_column(ForeignKey("lrm_principal.subject"), nullable=False)
    checker_id: Mapped[str | None] = mapped_column(ForeignKey("lrm_principal.subject"))
    rejected_by_id: Mapped[str | None] = mapped_column(ForeignKey("lrm_principal.subject"))
    source_document_sha256: Mapped[str | None] = mapped_column(String(64))
    verification_ref: Mapped[str | None] = mapped_column(Text)
    syariah_review_ref: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (
        UniqueConstraint("kind", "item_key", "version", name="uq_revision_version"),
        CheckConstraint("kind IN ('PARAMETER','MAPPING')", name="ck_revision_kind"),
        CheckConstraint("status IN ('DRAFT_UNVERIFIED','PENDING','ACTIVE','RETIRED')",
                        name="ck_revision_status"),
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from",
                        name="ck_revision_dates"),
        CheckConstraint("checker_id IS NULL OR checker_id <> maker_id",
                        name="ck_revision_four_eyes"),
        CheckConstraint("status NOT IN ('ACTIVE','RETIRED') OR (checker_id IS NOT NULL "
                        "AND approved_at IS NOT NULL AND submitted_at IS NOT NULL)",
                        name="ck_revision_approval_fields"),
        CheckConstraint("status <> 'ACTIVE' OR retirement = false",
                        name="ck_revision_active_nonretirement"),
        CheckConstraint("status <> 'RETIRED' OR retirement = true",
                        name="ck_revision_retired_tombstone"),
        CheckConstraint("status <> 'ACTIVE' OR kind <> 'PARAMETER' OR "
                        "(source_document_sha256 IS NOT NULL AND verification_ref IS NOT NULL)",
                        name="ck_parameter_verified"),
        CheckConstraint("status <> 'ACTIVE' OR kind <> 'MAPPING' OR syariah_review_ref IS NOT NULL",
                        name="ck_mapping_sharia_review"),
        Index("ix_rev_effective_lookup", "kind", "item_key", "effective_from"),
        Index("uq_approved_same_date", "kind", "item_key", "effective_from",
              unique=True, postgresql_where=text("status IN ('ACTIVE','RETIRED')"),
              sqlite_where=text("status IN ('ACTIVE','RETIRED')")),
    )


@event.listens_for(GovernedRevision, "before_update")
def forbid_orm_approved_edits(_mapper: object, _connection: object,
                              target: GovernedRevision) -> None:
    """Defense in depth; the production PostgreSQL trigger also enforces immutability."""
    from sqlalchemy import inspect
    state = inspect(target)
    old = state.attrs.status.history.deleted
    if old and old[0] in ("ACTIVE", "RETIRED"):
        raise ValueError("An approved/tombstone revision is immutable; make a new version")

# SQLite is only a local test double: DB-level immutability is mirrored here,
# while the PostgreSQL Alembic trigger also performs actor-role verification.
event.listen(
    GovernedRevision.__table__, "after_create",
    DDL("""CREATE TRIGGER trg_lrm_sqlite_approved_immutable
        BEFORE UPDATE ON lrm_governed_revision
        WHEN OLD.status IN ('ACTIVE','RETIRED')
        BEGIN SELECT RAISE(ABORT, 'approved revision immutable'); END;""").execute_if(dialect="sqlite"),
)
event.listen(
    GovernedRevision.__table__, "after_create",
    DDL("""CREATE TRIGGER trg_lrm_sqlite_no_delete
        BEFORE DELETE ON lrm_governed_revision
        BEGIN SELECT RAISE(ABORT, 'revision cannot be deleted'); END;""").execute_if(dialect="sqlite"),
)
