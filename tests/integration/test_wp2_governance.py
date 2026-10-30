"""WP2 SIT: real SQLite DB constraints; PostgreSQL triggers require UAT DB."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, DBAPIError

from lrm_data.schema import DatasetType
from lrm_engine.akad.classifier import classify, MappingNotFound
from lrm_services.models import Base, Principal
from lrm_services.governance import GovernanceService, GovernanceError
from lrm_services.akad_gateway import validate_batch_with_mapping, SOURCE_KEY_FIELDS
from scripts.generate_synthetic_inputs import SAMPLES, workbook_bytes

D = date(2026, 10, 30)
LEGAL = "Bank-approved test rule only; not official regulatory mapping"
REASON = "Synthetic WP2 acceptance test"
HASH = "b" * 64  # synthetic document SHA only, not actual regulatory attestation


@pytest.fixture
def session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            Principal(subject="maker-A", role="MAKER", enabled=True),
            Principal(subject="checker-B", role="CHECKER", enabled=True),
            Principal(subject="maker-C", role="MAKER", enabled=True),
            Principal(subject="auditor", role="AUDITOR", enabled=True),
            Principal(subject="admin", role="ADMINISTRATOR", enabled=True),
            Principal(subject="alco", role="ALCO", enabled=True),
            Principal(subject="disabled", role="CHECKER", enabled=False),
        ])
        db.commit()
        yield db
    engine.dispose()


def maker(db): return GovernanceService(db, "maker-A")
def checker(db): return GovernanceService(db, "checker-B")


def draft_param(db, key="LCR-CAP-TEST", value="0.75", start=D, end=None):
    return maker(db).draft_parameter(param_id=key, value=value, unit="ratio",
        effective_from=start, effective_to=end, legal_basis=LEGAL, change_reason=REASON)


def approve_param(db, param):
    maker(db).submit(param.id)
    return checker(db).approve(param.id, source_document_sha256=HASH,
                               verification_ref="Synthetic Bank test evidence, not regulation")


def draft_mapping(db, dataset="Deposito", source_key="DEP-SYN", akad="mudharabah", start=D):
    return maker(db).draft_mapping(dataset=dataset, source_key=source_key, akad=akad,
        balance_side="LIABILITY", lcr_category="SYN_LCR_DPK",
        nsfr_category="SYN_NSFR_ASF", rule_id="SYNTHETIC-TEST-MAP",
        effective_from=start, legal_basis=LEGAL, change_reason=REASON)


def approve_mapping(db, record):
    maker(db).submit(record.id)
    return checker(db).approve(record.id,
                              syariah_review_ref="SYNTHETIC-TEST-DPS-REF")


def test_draft_unverified_seed_remains_non_effective(session):
    p = draft_param(session, value=None)
    assert p.status == "DRAFT_UNVERIFIED"
    assert checker(session).parameter(p.item_key, D) is None
    with pytest.raises(GovernanceError, match="Null"):
        maker(session).submit(p.id)


def test_parameter_requires_independent_checker_evidence(session):
    p = draft_param(session)
    maker(session).submit(p.id)
    assert checker(session).parameter(p.item_key, D) is None
    with pytest.raises(PermissionError):
        maker(session).approve(p.id, source_document_sha256=HASH,
                              verification_ref="Test")
    with pytest.raises(GovernanceError, match="SHA-256"):
        checker(session).approve(p.id)
    with pytest.raises(GovernanceError, match="verification_ref"):
        checker(session).approve(p.id, source_document_sha256=HASH,
                                 verification_ref="[VERIFY]")
    approved = checker(session).approve(p.id, source_document_sha256=HASH,
                                        verification_ref="SYNTHETIC-TEST-SOURCE")
    assert approved.status == "ACTIVE"
    assert checker(session).parameter(p.item_key, D) == (Decimal("0.75"), "ratio", 1)
    assert checker(session).parameter(p.item_key, date(2026, 10, 29)) is None


def test_role_privileges_forbidden(session):
    for role in ("checker-B", "auditor", "admin", "alco", "disabled"):
        if role == "disabled":
            with pytest.raises(PermissionError): GovernanceService(session, role)
        else:
            with pytest.raises(PermissionError): GovernanceService(session, role).draft_parameter(
                param_id="x", value="1", unit="ratio", effective_from=D,
                legal_basis=LEGAL, change_reason=REASON)
    p = draft_param(session); maker(session).submit(p.id)
    for role in ("auditor", "admin", "alco", "maker-C"):
        with pytest.raises(PermissionError):
            GovernanceService(session, role).approve(p.id,
                source_document_sha256=HASH, verification_ref="SYN-REF")


def test_rejected_revision_requires_resubmission(session):
    p = draft_param(session)
    maker(session).submit(p.id)
    checker(session).reject(p.id, reason="Missing review")
    assert p.status == "DRAFT_UNVERIFIED"
    assert p.rejected_by_id == "checker-B"
    with pytest.raises(GovernanceError, match="pending"):
        checker(session).approve(p.id, source_document_sha256=HASH, verification_ref="SYN-REF")
    maker(session).submit(p.id)
    approve = checker(session).approve(p.id, source_document_sha256=HASH,
                                      verification_ref="SYN-REF")
    assert approve.status == "ACTIVE"


def test_db_check_constraint_maker_cannot_self_approve_even_via_sql(session):
    p = draft_param(session)
    maker(session).submit(p.id)
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.execute(text("UPDATE lrm_governed_revision SET checker_id=maker_id "
                                 "WHERE id=:id"), {"id": p.id})


def test_approved_revisions_immutable_even_via_direct_sql(session):
    p = draft_param(session)
    approve_param(session, p)
    with pytest.raises(DBAPIError):
        with session.begin_nested():
            session.execute(text("UPDATE lrm_governed_revision SET change_reason='tamper' "
                                 "WHERE id=:id"), {"id": p.id})
    with pytest.raises(DBAPIError):
        with session.begin_nested():
            session.execute(text("DELETE FROM lrm_governed_revision WHERE id=:id"),
                            {"id": p.id})


def test_latest_as_of_versions_and_retirement_tombstone(session):
    p1 = draft_param(session, value="0.5", start=date(2026, 1, 1))
    approve_param(session, p1)
    p2 = draft_param(session, value="0.8", start=date(2026, 12, 1), end=date(2026, 12, 31))
    approve_param(session, p2)
    svc = checker(session)
    assert svc.parameter(p1.item_key, date(2026, 10, 30))[0] == Decimal("0.5")
    assert svc.parameter(p1.item_key, date(2026, 12, 15))[0] == Decimal("0.8")
    assert svc.parameter(p1.item_key, date(2027, 1, 1)) is None  # no fallback
    tombstone = maker(session).draft_retirement(kind="PARAMETER", item_key=p1.item_key,
                        effective_from=date(2026, 12, 20), legal_basis=LEGAL,
                        change_reason="Synthetic policy decommissioning")
    maker(session).submit(tombstone.id)
    checker(session).approve(tombstone.id)
    assert svc.parameter(p1.item_key, date(2026, 12, 15))[0] == Decimal("0.8")
    assert svc.parameter(p1.item_key, date(2026, 12, 22)) is None
    assert p1.status == "ACTIVE"  # history preserved


def test_no_same_date_double_active(session):
    p1 = draft_param(session); approve_param(session, p1)
    p2 = draft_param(session, value="0.9")
    maker(session).submit(p2.id)
    with pytest.raises(GovernanceError, match="already starts"):
        checker(session).approve(p2.id, source_document_sha256=HASH,
                                 verification_ref="SYN-REF")


def test_param_decimal_float_is_rejected(session):
    with pytest.raises(TypeError):
        draft_param(session, value=0.4)
    p = draft_param(session, value="0.000000000000000000000123456789")
    approve_param(session, p)
    assert str(checker(session).parameter(p.item_key, D)[0]) == "1.23456789E-22"


def test_mapping_requires_dps_evidence_and_match(session):
    rev = draft_mapping(session)
    maker(session).submit(rev.id)
    with pytest.raises(GovernanceError, match="syariah_review_ref"):
        checker(session).approve(rev.id)
    checker(session).approve(rev.id, syariah_review_ref="SYNTHETIC-TEST-DPS-REF")
    mapping = checker(session).mapping("Deposito", "DEP-SYN", D)
    assert mapping is not None
    assert classify(dataset="Deposito", source_key="DEP-SYN", akad="mudharabah",
                    as_of=D, mapping=mapping) == ("SYN_LCR_DPK", "SYNTHETIC-TEST-MAP", 1)
    with pytest.raises(MappingNotFound):
        classify(dataset="Deposito", source_key="DEP-SYN", akad="wadiah", as_of=D,
                 mapping=mapping)
    assert checker(session).mapping("Deposito", "OTHER", D) is None


def test_service_integration_mapping_coverage_all_synthetic_rows(session):
    files = {f"{x.value}.xlsx": workbook_bytes(x) for x in DatasetType}
    before = validate_batch_with_mapping(files, service=checker(session),
             reporting_date=D, reporting_currency="IDR", required_datasets=list(DatasetType))
    assert before.batch.report.status == "FAILED"
    assert any(f.rule_id == "DQ-AKAD-004" for f in before.batch.report.findings)
    # All categories here are deliberately synthetic Bank test placeholders, not live regulatory categories.
    created: set[tuple[str,str]] = set()
    for ds in DatasetType:
        field = SOURCE_KEY_FIELDS.get(ds)
        if field is None: continue
        for row in SAMPLES[ds]:
            key = str(row[field])
            if (ds.value,key) in created: continue
            rec = draft_mapping(session, dataset=ds.value, source_key=key, akad=row['akad'])
            approve_mapping(session, rec)
            created.add((ds.value,key))
    # Mappings alone must NOT unblock regulatory calculations without active parameters.
    without_parameters = validate_batch_with_mapping(files, service=checker(session),
            reporting_date=D, reporting_currency="IDR", required_datasets=list(DatasetType))
    assert any(x.rule_id == "DQ-PARAM-001" for x in without_parameters.batch.report.findings)
    assert not without_parameters.batch.report.calculation_allowed
    test_param = draft_param(session, key="SYN-TEST-REQUIRED-PARAM", value="0.1")
    approve_param(session, test_param)
    after = validate_batch_with_mapping(files, service=checker(session),
            reporting_date=D, reporting_currency="IDR", required_datasets=list(DatasetType),
            required_parameter_ids=["SYN-TEST-REQUIRED-PARAM"])
    assert after.batch.report.status == "PASS"
    assert len(after.mapping_traces) == sum(len(SAMPLES[ds]) for ds in SOURCE_KEY_FIELDS)
    assert all(t.mapping_version >= 1 and len(t.source_file_hash) == 64 for t in after.mapping_traces)
    assert after.parameter_set_hash is not None and len(after.parameter_set_hash) == 64


def test_source_akad_mismatch_causes_failed_gate(session):
    rec = draft_mapping(session, dataset="Deposito", source_key="DEP-SYN", akad="wadiah")
    approve_mapping(session, rec)
    files = {"Deposito.xlsx": workbook_bytes(DatasetType.DEPOSITO)}
    report = validate_batch_with_mapping(files, service=checker(session),
        reporting_date=D, reporting_currency="IDR", required_datasets=[DatasetType.DEPOSITO])
    assert report.batch.report.status == "FAILED"


def test_parameter_active_not_allowed_from_direct_insert_without_checker(session):
    p = draft_param(session)
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.execute(text("UPDATE lrm_governed_revision SET status='ACTIVE' WHERE id=:id"),
                            {"id": p.id})


def test_placeholder_regulatory_basis_cannot_submit(session):
    p = maker(session).draft_parameter(param_id="TEST", value="1", unit="ratio",
        effective_from=D, legal_basis="POJK 20/2025 [VERIFY]", change_reason=REASON)
    with pytest.raises(GovernanceError, match="legal_basis"):
        maker(session).submit(p.id)


def test_backdated_approved_revision_rejected(session):
    first = draft_param(session, start=date(2026, 10, 1))
    approve_param(session, first)
    earlier = draft_param(session, value="0.9", start=date(2026, 9, 1))
    maker(session).submit(earlier.id)
    with pytest.raises(GovernanceError, match="Backdated"):
        checker(session).approve(earlier.id, source_document_sha256=HASH,
                                 verification_ref="SYN-REF")


def test_parameter_snapshot_is_canonical_order_invariant(session):
    a = draft_param(session, key="A", value="1.0"); approve_param(session, a)
    b = draft_param(session, key="B", value="2.000"); approve_param(session, b)
    one, h1 = checker(session).parameter_snapshot(["B", "A"], D)
    two, h2 = checker(session).parameter_snapshot(["A", "B"], D)
    assert h1 == h2 and one == two
    with pytest.raises(GovernanceError): checker(session).parameter_snapshot([], D)
    with pytest.raises(GovernanceError): checker(session).parameter_snapshot(["A", "A"], D)
    with pytest.raises(GovernanceError): checker(session).parameter_snapshot(["A", "MISSING"], D)
