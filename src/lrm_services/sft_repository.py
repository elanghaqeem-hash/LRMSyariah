"""Append-only governed SFT trade/leg snapshot bound to one WP3 LCR run.

Raw documents remain in Bank vault; only pseudonymized transaction parcels and
SHA-linked evidence stored with the Bank database. SQLite test-double triggers
are not a substitute for PostgreSQL restricted DB roles.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any

from sqlalchemy import CheckConstraint, Date, DDL, ForeignKey, Integer, String, Text, event, text
from sqlalchemy.orm import Mapped, Session, mapped_column

from lrm_engine.common.canonical import canonical_json, sha256_canonical
from lrm_engine.lcr.sft_ledger import SFTLedger, ledger_from_snapshot
from lrm_services.models import Base, Principal
from lrm_services.runs import CalculationRun, RunError, RunService


class SFTRunLedger(Base):
    __tablename__ = "lrm_sft_run_ledger"

    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("lrm_calculation_run.id"), primary_key=True)
    maker_id: Mapped[str] = mapped_column(String(180), ForeignKey("lrm_principal.subject"), nullable=False)
    position_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_batch_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    stock_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    ledger_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    trade_count: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    __table_args__ = (CheckConstraint("trade_count > 0",name="ck_sft_trade_count"),)


for op in ("UPDATE", "DELETE"):
    event.listen(SFTRunLedger.__table__,"after_create",DDL(
      f"CREATE TRIGGER lrm_sft_no_{op.lower()} BEFORE {op} ON lrm_sft_run_ledger "
      "BEGIN SELECT RAISE(ABORT, 'SFT record append-only'); END"
    ).execute_if(dialect="sqlite"))


def _sha(blob: str) -> str:
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def attach_sft_ledger(session: Session, maker: str, run: CalculationRun,
                      ledger: SFTLedger) -> SFTRunLedger:
    principal=session.get(Principal,maker)
    if (principal is None or not principal.enabled or principal.role != "MAKER"
            or run.status != "DRAFT" or run.maker_id != maker
            or run.run_type not in ("LCR_DAILY","LCR_MONTHLY")):
        raise PermissionError("Only owner maker may append SFT ledger to draft LCR")
    try:
        inputs: dict[str, Any] = json.loads(run.input_snapshot)
        record_ledger = ledger_from_snapshot(inputs["sft_ledger"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RunError("Calculation run is missing its immutable SFT snapshot") from exc
    digest=sha256_canonical(ledger)
    if (digest != sha256_canonical(record_ledger) or inputs.get("sft_ledger_sha256") != digest
            or run.reporting_date != ledger.reporting_date):
        raise RunError("SFT ledger does not match the frozen calculation run")
    blob=canonical_json(ledger).decode()
    row=SFTRunLedger(run_id=run.id,maker_id=maker,position_date=ledger.reporting_date,
        source_batch_sha256=ledger.source_batch_sha256,
        stock_sha256=ledger.hqla_stock_sha256,ledger_sha256=digest,
        trade_count=len(ledger.trades),snapshot_json=blob)
    if session.bind is not None and session.bind.dialect.name=="postgresql":
        session.execute(text("SELECT set_config('lrm.actor_id', :who, true)"),{"who":maker})
    session.add(row)
    session.flush()
    RunService(session,maker)._audit("SFT_LEDGER_ATTACHED",run.id,{"ledger_sha256":digest,
        "source_sha256":ledger.source_batch_sha256,"trade_count":len(ledger.trades)})
    return row


def verify_sft_ledger_bound(session: Session,run:CalculationRun) -> str:
    try:
        inputs:dict[str,Any] = json.loads(run.input_snapshot)
    except (ValueError,TypeError) as exc:
        raise RunError("Unverifiable LCR snapshot") from exc
    has=inputs.get("has_unwind_transactions")
    if has is False:
        if inputs.get("sft_ledger") is not None or session.get(SFTRunLedger,run.id) is not None:
            raise RunError("SFT snapshot exists but unwind is not declared")
        return "NO_SHORT_TERM_SFT_DECLARED"
    if has is not True:
        raise RunError("LCR must explicitly declare a governed unwind state")
    record=session.get(SFTRunLedger,run.id)
    if record is None:
        raise RunError("SFT run lacks a separately appended immutable ledger")
    if (record.maker_id != run.maker_id or record.position_date != run.reporting_date
            or _sha(record.snapshot_json)!=record.ledger_sha256
            or inputs.get("sft_ledger_sha256")!=record.ledger_sha256
            or record.source_batch_sha256 != inputs.get("sft_ledger",{}).get("source_batch_sha256")):
        raise RunError("SFT immutable proof is inconsistent with calculation run")
    try:
        parsed=json.loads(record.snapshot_json)
        ledger=ledger_from_snapshot(parsed)
    except (ValueError,TypeError) as exc:
        raise RunError("Invalid persisted SFT evidence") from exc
    if (sha256_canonical(ledger)!=record.ledger_sha256 or
        sha256_canonical(ledger)!=sha256_canonical(inputs["sft_ledger"]) or
        record.trade_count != len(ledger.trades)):
        raise RunError("SFT ledger hash or trade count mismatch")
    return record.ledger_sha256