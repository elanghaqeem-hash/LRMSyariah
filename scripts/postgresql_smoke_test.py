"""Ephemeral PostgreSQL 16 synthetic migration/SoD/immutability smoke.

DO NOT RUN against a real Bank database: inserts and test DML are deliberately
synthetic and cannot replace restricted-role or bank-specific UAT.
"""
from __future__ import annotations

import os
import uuid
from datetime import date

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session

from lrm_services.models import Principal
from lrm_services.runs import RunService, verify_ledger


def expect_denied(engine: object, sql: str, params: dict[str, str]) -> None:
    try:
        with engine.begin() as connection:  # type: ignore[attr-defined]
            connection.execute(text(sql), params)
    except DatabaseError:
        return
    raise AssertionError("Direct SQL modification unexpectedly succeeded")


def main() -> None:
    url = os.environ.get("LRM_DATABASE_URL", "")
    if "lrm_ci" not in url or "localhost" not in url:
        raise RuntimeError("Only throwaway local lrm_ci PostgreSQL is permitted")
    engine = create_engine(url)
    try:
        assert engine.dialect.name == "postgresql"
        tables = set(inspect(engine).get_table_names())
        assert {"lrm_principal", "lrm_governed_revision", "lrm_calculation_run",
                "lrm_audit_event", "lrm_lcr_run_evidence", "lrm_lcr_recon_case"} <= tables
        assert {"trg_lrm_revision_guard"} <= {t[0] for t in engine.connect().execute(
            text("SELECT tgname FROM pg_trigger WHERE NOT tgisinternal")).all()}
        maker = "smoke-maker-" + uuid.uuid4().hex[:16]
        checker = "smoke-checker-" + uuid.uuid4().hex[:16]
        with Session(engine) as session:
            session.add_all([Principal(subject=maker,role="MAKER",enabled=True),
                             Principal(subject=checker,role="CHECKER",enabled=True)])
            session.commit()
            service=RunService(session,maker)
            obj=service.create(reporting_date=date(2026,10,31),run_type="STRESS",
                 engine_version="0.4.0+abcdef123456", parameter_set_version="synthetic-p1",
                 akad_mapping_version="synthetic-s1",input_data={"amount":"5"},
                 parameters={"multiply":"2"})
            rid=obj.id
            session.commit()
            service=RunService(session,maker)
            service.validate(rid,calculator=lambda i,p: {"result":str(int(i["amount"])*int(p["multiply"]))},
                             dq_passed=True,reconciliation_passed=True)
            session.commit()
            RunService(session,maker).submit(rid)
            session.commit()
            RunService(session,checker).approve(rid)
            session.commit()
            assert verify_ledger(session) == 4
            assert RunService(session,checker).reproduce(rid,calculator=lambda i,p: {"result":str(int(i["amount"])*int(p["multiply"]))},
                                                         engine_version="0.4.0+abcdef123456")
        expect_denied(engine,"UPDATE lrm_calculation_run SET result_sha256=:new WHERE id=:rid",
                      {"new":"f"*64,"rid":rid})
        expect_denied(engine,"DELETE FROM lrm_audit_event WHERE sequence=1",{})
        with Session(engine) as session:
            assert verify_ledger(session)==4
        print("PASS: real isolated PostgreSQL migrations, maker-checker, immutable approved run and hash ledger")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()