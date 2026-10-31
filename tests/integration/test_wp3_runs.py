"""WP3 R13/R16: synthetic-only CalculationRun and append-only chain tests."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import DatabaseError

from lrm_services.models import Base, Principal
from lrm_services.runs import AuditEvent, RunError, RunService, verify_ledger

VERSION = '0.3.0+deadbeef'


def calculate(inputs, params):
    return {'sum': str(Decimal(inputs['saldo']) + Decimal(params['delta']))}


@pytest.fixture
def db():
    engine = create_engine('sqlite+pysqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([Principal(subject='maker', role='MAKER'),
                         Principal(subject='checker', role='CHECKER'),
                         Principal(subject='second', role='MAKER'),
                         Principal(subject='auditor', role='AUDITOR')])
        session.commit()
        yield session
    engine.dispose()


def draft(db):
    return RunService(db, 'maker').create(
        reporting_date=date(2026, 10, 30), run_type='STRESS',
        engine_version=VERSION, parameter_set_version='approved-param-v3',
        akad_mapping_version='reviewed-akad-v4',
        input_data={'saldo': Decimal('100.00')}, parameters={'delta': Decimal('25.00')})


def approved(db):
    run = draft(db)
    maker = RunService(db, 'maker')
    maker.validate(run.id, calculator=calculate, dq_passed=True, reconciliation_passed=True)
    maker.submit(run.id)
    RunService(db, 'checker').approve(run.id)
    db.commit()
    return run


def test_end_to_end_reproduce_exact(db):
    run = approved(db)
    assert run.status == 'APPROVED'
    assert RunService(db, 'auditor').reproduce(run.id, calculator=calculate, engine_version=VERSION) == run.result_sha256
    assert verify_ledger(db) == 4


def test_repro_wrong_engine_refused(db):
    run = approved(db)
    with pytest.raises(RunError, match='Engine version mismatch'):
        RunService(db, 'auditor').reproduce(run.id, calculator=calculate, engine_version='9.0.0+deadbeef')


def test_repro_wrong_calculation_refused(db):
    run = approved(db)
    with pytest.raises(RunError, match='Reproduction hash mismatch'):
        RunService(db, 'auditor').reproduce(run.id, calculator=lambda a, b: {'sum': '125.001'}, engine_version=VERSION)


def test_refuse_dq_and_reconciliation_failed(db):
    run = draft(db)
    maker = RunService(db, 'maker')
    for dq, recon in [(False, True), (True, False)]:
        with pytest.raises(RunError):
            maker.validate(run.id, calculator=calculate, dq_passed=dq, reconciliation_passed=recon)
    assert run.status == 'DRAFT'


def test_maker_checker_roles_enforced(db):
    run = draft(db)
    with pytest.raises(PermissionError):
        RunService(db, 'checker').validate(run.id, calculator=calculate, dq_passed=True, reconciliation_passed=True)
    maker = RunService(db, 'maker')
    maker.validate(run.id, calculator=calculate, dq_passed=True, reconciliation_passed=True)
    maker.submit(run.id)
    with pytest.raises(PermissionError):
        maker.approve(run.id)
    with pytest.raises(PermissionError):
        RunService(db, 'auditor').approve(run.id)


def test_immutable_approved_raw_sql(db):
    run = approved(db)
    with pytest.raises(DatabaseError):
        db.execute(text("UPDATE lrm_calculation_run SET result_sha256 = :val WHERE id=:id"),
                   {'val': 'b' * 64, 'id': run.id})
    db.rollback()
    with pytest.raises(DatabaseError):
        db.execute(text('DELETE FROM lrm_calculation_run WHERE id=:id'), {'id': run.id})
    db.rollback()


def test_audit_append_only_raw_sql(db):
    approved(db)
    with pytest.raises(DatabaseError):
        db.execute(text('DELETE FROM lrm_audit_event WHERE sequence = 1'))
    db.rollback()
    with pytest.raises(DatabaseError):
        db.execute(text("UPDATE lrm_audit_event SET event_type = 'HIDE' WHERE sequence = 1"))
    db.rollback()
    assert verify_ledger(db) == 4


def test_detect_tampered_memory_event(db):
    approved(db)
    event = db.get(AuditEvent, 1)
    event.previous_hash = 'f' * 64
    with pytest.raises(RunError, match='previous hash mismatch'):
        verify_ledger(db)
    db.expunge(event)
    db.rollback()


def test_supersession_preserves_history(db):
    previous = approved(db)
    second = RunService(db, 'maker').create(
        reporting_date=date(2026, 10, 30), run_type='STRESS',
        engine_version=VERSION, parameter_set_version='approved-param-v5',
        akad_mapping_version='reviewed-akad-v4', input_data={'saldo': '101'},
        parameters={'delta': '25'}, supersedes_run_id=previous.id,
        change_reason='Correction requested by checker')
    assert previous.status == 'APPROVED'
    assert second.supersedes_run_id == previous.id
    assert verify_ledger(db) == 5


def test_supersession_requires_approved_and_reason(db):
    old = draft(db)
    with pytest.raises(RunError):
        RunService(db, 'maker').create(
            reporting_date=date(2026, 10, 30), run_type='STRESS',
            engine_version=VERSION, parameter_set_version='x', akad_mapping_version='y',
            input_data={}, parameters={}, supersedes_run_id=old.id, change_reason='No')


def test_nofloat_no_weak_engine_version(db):
    maker = RunService(db, 'maker')
    with pytest.raises(TypeError):
        maker.create(reporting_date=date(2026, 10, 30), run_type='STRESS',
                     engine_version=VERSION, parameter_set_version='v1', akad_mapping_version='v1',
                     input_data={'saldo': 12.5}, parameters={})
    with pytest.raises(RunError):
        maker.create(reporting_date=date(2026, 10, 30), run_type='STRESS',
                     engine_version='dev', parameter_set_version='v1', akad_mapping_version='v1',
                     input_data={}, parameters={})


def test_audit_metadata_event(db):
    RunService(db, 'maker').record_event('UPLOAD', str(date(2026, 10, 30)), file_sha256='a' * 64)
    assert verify_ledger(db) == 1
    with pytest.raises(RunError):
        RunService(db, 'maker').record_event('EXPORT', 'obj', file_sha256='bad')


def test_reject_with_reason(db):
    run = draft(db)
    maker = RunService(db, 'maker')
    maker.validate(run.id, calculator=calculate, dq_passed=True, reconciliation_passed=True)
    maker.submit(run.id)
    RunService(db, 'checker').reject(run.id, 'Sumber tidak lengkap')
    assert run.status == 'REJECTED'
    assert verify_ledger(db) == 4