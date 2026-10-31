"""Synthetic-only issue #4: 13-file -> WP2 -> LCR -> GL -> WP3 approval/repro."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session

from lrm_data.reconciliation import ReconPolicy
from lrm_data.schema import DatasetType
from lrm_services.akad_gateway import SOURCE_KEY_FIELDS
from lrm_services.governance import GovernanceService
from lrm_services.lcr_evidence import LCRReconCase, LCRRunEvidence, review_reconciliation_case
from lrm_services.lcr_pipeline import (
    LCRGateError, LCRSourcePolicy, _lcr_calculator, create_evidence_bound_lcr_run, prepare_lcr,
)
from lrm_services.models import Base, Principal
from lrm_services.runs import RunError, RunService, verify_ledger
from scripts.generate_synthetic_inputs import SAMPLES, workbook_bytes

D = date(2026, 10, 30)
ENGINE = "0.4.0+abcdef123456"
FAKE_SHA = "e" * 64
APPROVED_SYNTHETIC = "SYNTHETIC-REVIEW-ONLY-NOT-BANK-APPROVAL"
CATEGORIES = {
    "PenempatanBI": "HQLA:L1:haircut.bi",
    "SuratBerhargaSyariah": "HQLA:L2A:haircut.suk",
    "PenempatanBankLain": "INFLOW:inflow.bank",
    "GiroTabungan": "OUTFLOW:outflow.giro",
    "Deposito": "OUTFLOW:outflow.depo",
    "KewajibanAntarBank": "OUTFLOW:outflow.interbank",
    "Pembiayaan": "INFLOW:inflow.financing",
    "Kontinjensi": "OUTFLOW:outflow.contingent",
    "DistribusiBagiHasil": "EXCLUDE",
}
FACTOR_VALUES = {
    "hqlacap.level2": "0.4", "hqlacap.level2b": "0.15", "inflow.cap": "0.75",
    "haircut.bi": "0", "haircut.suk": "0.15", "inflow.bank": "1",
    "outflow.giro": "0.1", "outflow.depo": "0.15", "outflow.interbank": "1",
    "inflow.financing": "1", "outflow.contingent": "0.05",
}


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        s.add_all([Principal(subject="maker", role="MAKER"),
                   Principal(subject="checker", role="CHECKER"),
                   Principal(subject="audit", role="AUDITOR")])
        s.commit()
        yield s
    engine.dispose()


def fixture_files():
    return {f"{ds.value}.xlsx": workbook_bytes(ds) for ds in DatasetType}


def setup_governance(db: Session) -> GovernanceService:
    maker = GovernanceService(db, "maker")
    checker = GovernanceService(db, "checker")
    for key, value in FACTOR_VALUES.items():
        revision = maker.draft_parameter(param_id=key, value=value, unit="fraction",
             effective_from=D, legal_basis=APPROVED_SYNTHETIC,
             change_reason="Synthetic model engineering test")
        maker.submit(revision.id)
        checker.approve(revision.id, source_document_sha256=FAKE_SHA,
                        verification_ref=APPROVED_SYNTHETIC)
    for ds in DatasetType:
        field = SOURCE_KEY_FIELDS.get(ds)
        if field is None:
            continue
        for row in SAMPLES[ds]:
            revision = maker.draft_mapping(dataset=ds.value, source_key=str(row[field]),
                akad=row["akad"], balance_side="ASSET", lcr_category=CATEGORIES[ds.value],
                nsfr_category="SYNTHETIC-NSFR-TEST", rule_id=f"SYN-{ds.value}",
                effective_from=D, legal_basis=APPROVED_SYNTHETIC,
                change_reason="Synthetic sharia classifier test")
            maker.submit(revision.id)
            checker.approve(revision.id, syariah_review_ref=APPROVED_SYNTHETIC)
    return maker


def scope():
    return LCRSourcePolicy(gl_signs={f"GL-{n:03}": 1 for n in range(1, 8)},
            scope_approval_ref=APPROVED_SYNTHETIC, scope_document_sha256=FAKE_SHA,
            has_unwind_transactions=False, unwind_review_ref=APPROVED_SYNTHETIC,
            recon_policy=ReconPolicy(tolerance=Decimal("0"),
                approval_ref=APPROVED_SYNTHETIC, legal_basis=APPROVED_SYNTHETIC,
                parameter_version="SYNTHETIC-RECON-POLICY-V1"))


def prepared(db, files=None, policy=None):
    gov = setup_governance(db)
    return prepare_lcr(files=files or fixture_files(), governance=gov,
                       reporting_date=D, reporting_currency="IDR", source_policy=policy or scope())


def test_13_source_lcr_dq_recon_and_run_reproduction(db):
    batch = prepared(db)
    assert len(batch.source_hashes) == 13
    assert batch.data_quality["status"] == "PASS"
    assert batch.reconciliation["status"] == "PASS"
    assert len(batch.reconciliation["lines"]) == 7
    run_id = create_evidence_bound_lcr_run(session=db, maker_subject="maker",
                                             prepared=batch, engine_version=ENGINE)
    run = RunService(db, "maker")._get(run_id, "VALIDATED")
    assert run.dq_summary == "PASS" and run.recon_summary == "PASS"
    assert db.get(LCRRunEvidence, run_id).evidence_sha256
    RunService(db, "maker").submit(run_id)
    with pytest.raises(PermissionError):
        RunService(db, "maker").approve(run_id)
    RunService(db, "checker").approve(run_id)
    assert RunService(db, "audit").reproduce(run_id, calculator=_lcr_calculator,
                                               engine_version=ENGINE) == run.result_sha256
    assert verify_ledger(db) == 5


def test_lcr_boolean_approval_bypass_blocked(db):
    maker = RunService(db, "maker")
    run = maker.create(reporting_date=D, run_type="LCR_DAILY", engine_version=ENGINE,
                 parameter_set_version="synthetic", akad_mapping_version="synthetic",
                 input_data={"hello": "world"}, parameters={"something": "test"})
    with pytest.raises(RunError, match="evidence"):
        maker.validate(run.id, calculator=lambda i, p: {"fake": "1"},
                       dq_passed=True, reconciliation_passed=True)
    assert run.status == "DRAFT"


def test_fail_closed_missing_mapping(db):
    gov = GovernanceService(db, "maker")
    with pytest.raises(LCRGateError, match="DQ"):
        prepare_lcr(files=fixture_files(), governance=gov, reporting_date=D,
                    reporting_currency="IDR", source_policy=scope())


def test_reject_missing_source_dataset(db):
    setup_governance(db)
    files = fixture_files()
    del files["Deposito.xlsx"]
    with pytest.raises(LCRGateError, match="13-source"):
        prepare_lcr(files=files, governance=GovernanceService(db, "maker"),
                    reporting_date=D, reporting_currency="IDR", source_policy=scope())


def test_gl_variance_persists_exception_but_never_validates(db):
    from scripts.generate_synthetic_inputs import SAMPLES
    files = fixture_files()
    changed = [dict(SAMPLES[DatasetType.NERACA_HARIAN][0], saldo="100002")]
    changed += SAMPLES[DatasetType.NERACA_HARIAN][1:]
    files["NeracaHarian.xlsx"] = workbook_bytes(DatasetType.NERACA_HARIAN, rows=changed)
    batch = prepared(db, files=files)
    assert batch.reconciliation["status"] == "FAILED"
    run_id = create_evidence_bound_lcr_run(session=db, maker_subject="maker",
                                             prepared=batch, engine_version=ENGINE)
    run = RunService(db, "maker")._get(run_id, "DRAFT")
    cases = db.scalars(select(LCRReconCase).where(LCRReconCase.run_id == run_id)).all()
    assert len(cases) == 1 and cases[0].severity == "HIGH"
    with pytest.raises(RunError, match="reconciliation PASS"):
        RunService(db, "maker").validate(run_id, calculator=_lcr_calculator,
                                         dq_passed=True, reconciliation_passed=True)
    with pytest.raises(PermissionError):
        review_reconciliation_case(db, "maker", cases[0].id, "review")
    review_reconciliation_case(db, "checker", cases[0].id,
                              "Synthetic GL correction required; no waiver")
    assert cases[0].status == "REVIEWED" and run.status == "DRAFT"
    db.commit()
    with pytest.raises(DatabaseError):
        db.execute(text("DELETE FROM lrm_lcr_recon_case WHERE id = :x"), {"x": cases[0].id})
    db.rollback()


def test_recon_scope_missing_gl_blocked(db):
    gov = setup_governance(db)
    policy = LCRSourcePolicy(gl_signs={"GL-001": 1},
       scope_approval_ref=APPROVED_SYNTHETIC, scope_document_sha256=FAKE_SHA,
       has_unwind_transactions=False, unwind_review_ref=APPROVED_SYNTHETIC,
       recon_policy=scope().recon_policy)
    with pytest.raises(LCRGateError, match="GL scope"):
        prepare_lcr(files=fixture_files(), governance=gov,
                    reporting_date=D, reporting_currency="IDR", source_policy=policy)


def test_unwind_does_not_silently_execute():
    with pytest.raises(LCRGateError, match="unwind"):
        LCRSourcePolicy(gl_signs={"GL-001": 1},
             scope_approval_ref="synthetic", scope_document_sha256=FAKE_SHA,
             has_unwind_transactions=True, unwind_review_ref="synthetic",
             recon_policy=scope().recon_policy)


def test_proof_immutability_and_hash_tampering(db):
    batch = prepared(db)
    run_id = create_evidence_bound_lcr_run(session=db, maker_subject="maker",
                                             prepared=batch, engine_version=ENGINE)
    db.commit()
    with pytest.raises(DatabaseError):
        db.execute(text("UPDATE lrm_lcr_run_evidence SET evidence_sha256=:x WHERE run_id=:id"),
                   {"x": "a" * 64, "id": run_id})
    db.rollback()
    with pytest.raises(DatabaseError):
        db.execute(text("DELETE FROM lrm_lcr_run_evidence WHERE run_id=:id"), {"id": run_id})
    db.rollback()


def test_signed_gl_policy_and_no_float(db):
    with pytest.raises((LCRGateError, TypeError)):
        LCRSourcePolicy(gl_signs={"GL-001": 1.0}, scope_approval_ref="SYN",
              scope_document_sha256=FAKE_SHA, has_unwind_transactions=False,
              unwind_review_ref="SYN", recon_policy=scope().recon_policy)

def test_sft_unwind_13_sources_to_run_and_immutable_pg_equivalent(db):
    """Synthetic 13-source + approved-WP2 + settled SFT -> WP3 immutable run."""
    from dataclasses import replace
    from datetime import timedelta
    from lrm_engine.lcr.sft_ledger import SFTLedger, SFTTrade, UnwindLeg, stock_fingerprint
    from lrm_services.sft_repository import SFTRunLedger, verify_sft_ledger_bound
    from lrm_engine.common.canonical import sha256_canonical

    governance = setup_governance(db)
    baseline = prepare_lcr(files=fixture_files(), governance=governance,
                           reporting_date=D, reporting_currency="IDR", source_policy=scope())
    stock = {"L1": Decimal(0), "L2A": Decimal(0), "L2B": Decimal(0)}
    for item in baseline.input_snapshot["legs"]:
        if item["kind"] == "HQLA":
            factor = Decimal(baseline.parameter_snapshot["factors"][item["factor_key"]]["value"])
            stock[item["level"]] += Decimal(item["amount"]) * (Decimal(1) - factor)
    assert stock["L1"] > Decimal("1")
    ledger = SFTLedger(reporting_date=D,reporting_currency="IDR",
        source_batch_sha256=FAKE_SHA,hqla_stock_sha256=stock_fingerprint(stock),
        bank_sft_policy_ref=APPROVED_SYNTHETIC,bank_sft_policy_sha256=FAKE_SHA,
        trades=(SFTTrade(trade_id="SFT-abcdefgh",trade_kind="REPO_SYARIAH",akad="wakalah",
            trade_date=D-timedelta(days=6),settlement_date=D-timedelta(days=5),
            maturity_date=D+timedelta(days=30),currency="IDR",state="SETTLED_OPEN",
            signed_contract_sha256=FAKE_SHA,settlement_sha256=FAKE_SHA,
            legal_sharia_ref=APPROVED_SYNTHETIC,
            legs=(UnwindLeg(leg_id="LEG-abcdefgh",asset_id="ASSET-abcdefgh",
                level="L1",movement="RETURN_TO_COUNTERPARTY",post_haircut_value=Decimal("1"),
                counted_in_current_stock=True,security_eligibility_ref=APPROVED_SYNTHETIC,
                independent_price_ref=APPROVED_SYNTHETIC,custody_encumbrance_ref=APPROVED_SYNTHETIC,
                source_sha256=FAKE_SHA),
                UnwindLeg(leg_id="LEG-abcdefgi",asset_id="ASSET-abcdefgi",
                level="L2A",movement="RETURN_FROM_COUNTERPARTY",post_haircut_value=Decimal("1"),
                counted_in_current_stock=False,security_eligibility_ref=APPROVED_SYNTHETIC,
                independent_price_ref=APPROVED_SYNTHETIC,custody_encumbrance_ref=APPROVED_SYNTHETIC,
                source_sha256=FAKE_SHA))),))
    sft_policy = replace(scope(),has_unwind_transactions=True,sft_ledger=ledger)
    prepared_sft = prepare_lcr(files=fixture_files(), governance=governance,
        reporting_date=D,reporting_currency="IDR",source_policy=sft_policy)
    result = _lcr_calculator(prepared_sft.input_snapshot,prepared_sft.parameter_snapshot)
    assert result["adjusted_level1"] == stock["L1"] - Decimal(1)
    assert result["adjusted_level2a"] == stock["L2A"] + Decimal(1)
    assert result["sft_ledger_sha256"] == sha256_canonical(ledger)
    rid = create_evidence_bound_lcr_run(session=db,maker_subject="maker",
        prepared=prepared_sft,engine_version=ENGINE)
    assert db.get(SFTRunLedger,rid).trade_count == 1
    run = RunService(db,"maker")._get(rid,"VALIDATED")
    assert verify_sft_ledger_bound(db,run)==sha256_canonical(ledger)
    RunService(db,"maker").submit(rid)
    RunService(db,"checker").approve(rid)
    assert RunService(db,"audit").reproduce(rid,calculator=_lcr_calculator,
                                           engine_version=ENGINE) == run.result_sha256
    db.commit()
    with pytest.raises(DatabaseError):
        db.execute(text("DELETE FROM lrm_sft_run_ledger WHERE run_id=:rid"),{"rid":rid})
    db.rollback()


def test_working_paper_category_differential_on_integrated_lcr_synthetic(db):
    """No real Bank papers available: controlled synthetic reference only."""
    import hashlib
    from lrm_engine.common.canonical import canonical_json
    from lrm_services.lcr_differential import parse_working_paper_bytes,compare_working_paper
    from lrm_services.lcr_differential import WorkingPaperError

    batch=prepared(db)
    engine=_lcr_calculator(batch.input_snapshot,batch.parameter_snapshot)
    fields=("hqla","outflow","inflow_raw","inflow_used","net_cash_outflow","lcr",
            "level1","level2a","level2b","adjusted_level1","adjusted_level2a","adjusted_level2b")
    rules={}
    for rule,source_digest,amount in engine["trace"]:
        assert len(source_digest)==64
        rules[rule]=rules.get(rule,Decimal(0))+amount
    paper={"reporting_date":D.isoformat(),"currency":"IDR",
           "measures":{k:engine[k] for k in fields},"rule_amounts":rules}
    data=canonical_json(paper)
    bank=parse_working_paper_bytes(data,expected_sha256=hashlib.sha256(data).hexdigest(),
             approved_ref=APPROVED_SYNTHETIC,bank_approved_sha256=FAKE_SHA,synthetic_only=True)
    matched=compare_working_paper(bank=bank,engine=engine,reporting_date=D,currency="IDR",
        monetary_tolerance=Decimal("0"),ratio_tolerance=Decimal("0"),
        tolerance_approval_ref=APPROVED_SYNTHETIC)
    assert matched.status=="PASS"
    mismatch=dict(engine)
    mismatch["hqla"]=engine["hqla"]+Decimal(1)
    failed=compare_working_paper(bank=bank,engine=mismatch,reporting_date=D,currency="IDR",
        monetary_tolerance=Decimal("0"),ratio_tolerance=Decimal("0"),
        tolerance_approval_ref=APPROVED_SYNTHETIC)
    assert failed.status=="FAILED"
    mismatch["trace"]=()
    with pytest.raises(WorkingPaperError):
        compare_working_paper(bank=bank,engine=mismatch,reporting_date=D,currency="IDR",
            monetary_tolerance=Decimal("0"),ratio_tolerance=Decimal("0"),
            tolerance_approval_ref=APPROVED_SYNTHETIC)
