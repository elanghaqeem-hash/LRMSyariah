"""Differential cases are synthetic; no Bank working papers are available."""
from datetime import date
from decimal import Decimal
import hashlib
import json

import pytest

from lrm_services.lcr_differential import (
    parse_working_paper_bytes, compare_working_paper, WorkingPaperError,
)

D=date(2026,10,31)
H="a"*64
BASE={"hqla":"130","outflow":"100","inflow_raw":"50","inflow_used":"50",
      "net_cash_outflow":"50","lcr":"2.6","level1":"90","level2a":"30",
      "level2b":"10","adjusted_level1":"70","adjusted_level2a":"50",
      "adjusted_level2b":"10"}
TRACE=[("RULE-ASSET",H,"100"),("RULE-CASHFLOW",H,"30")]


def fixture(bank_delta="0",rules=None):
    metrics=dict(BASE)
    metrics["hqla"]=str(Decimal(metrics["hqla"])+Decimal(bank_delta))
    blob=json.dumps({"reporting_date":D.isoformat(),"currency":"IDR", "measures":metrics,
           "rule_amounts":rules or {"RULE-ASSET":"100","RULE-CASHFLOW":"30"}},sort_keys=True).encode()
    p=parse_working_paper_bytes(blob,expected_sha256=hashlib.sha256(blob).hexdigest(),
          approved_ref="SYNTHETIC-TEST-PAPER",bank_approved_sha256=H,synthetic_only=True)
    return p,blob


def engine():
    return {**BASE,"trace":TRACE}


def diff(paper,engine_result=None):
    return compare_working_paper(bank=paper,engine=engine_result or engine(),
        reporting_date=D,currency="IDR",monetary_tolerance=Decimal("0"),
        ratio_tolerance=Decimal("0"),tolerance_approval_ref="SYNTHETIC-TEST-TOLERANCE")


def test_synthetic_reference_exact_match_and_evidence_hash():
    p,_=fixture()
    result=diff(p)
    assert result.status=="PASS" and len(result.differences)==14
    assert result.evidence_sha256 and all(x.status=="PASS" for x in result.differences)


def test_differential_amount_variance_is_failed_not_waived():
    p,_=fixture("1")
    result=diff(p)
    assert result.status=="FAILED"
    assert [x.delta for x in result.differences if x.category=="hqla"]==[Decimal("-1")]


def test_unmapped_bank_category_fails_closed():
    p,_=fixture(rules={"RULE-UNKNOWN":"100"})
    with pytest.raises(WorkingPaperError,match="Unmatched"):
        diff(p)


def test_wrong_paper_hash_rejected():
    _,blob=fixture()
    with pytest.raises(WorkingPaperError,match="bytes differ"):
        parse_working_paper_bytes(blob,expected_sha256="0"*64,
            approved_ref="test",bank_approved_sha256=H,synthetic_only=True)


def test_mismatched_cutoff_currency_or_missing_rule_rejected():
    p,_=fixture()
    with pytest.raises(WorkingPaperError,match="cut-off"):
        compare_working_paper(bank=p,engine=engine(),reporting_date=date(2026,10,30),
            currency="IDR",monetary_tolerance=Decimal(0),ratio_tolerance=Decimal(0),
            tolerance_approval_ref="synthetic-tolerance")
    with pytest.raises(WorkingPaperError,match="trace"):
        diff(p, {k:v for k,v in engine().items() if k!="trace"})


def test_negative_tolerance_and_unapproved_tolerance_rejected():
    p,_=fixture()
    with pytest.raises(WorkingPaperError,match="cannot be negative"):
        compare_working_paper(bank=p,engine=engine(),reporting_date=D,currency="IDR",
            monetary_tolerance=Decimal("-1"),ratio_tolerance=Decimal(0),
            tolerance_approval_ref="test")
    with pytest.raises(WorkingPaperError,match="approved tolerances"):
        compare_working_paper(bank=p,engine=engine(),reporting_date=D,currency="IDR",
            monetary_tolerance=Decimal(0),ratio_tolerance=Decimal(0),
            tolerance_approval_ref="[VERIFY]")


@pytest.mark.parametrize('field,value,reason',[
    ('currency','idr','ISO 4217'),
    ('paper_sha256','bad','digest'),
    ('bank_approved_sha256','bad','digest'),
    ('bank_approved_ref','','Bank approval'),
    ('measures',{'hqla':'1'},'Missing or extra'),
    ('rule_amounts',{},'Missing or extra'),
])
def test_reject_invalid_paper_contract(field,value,reason):
    from dataclasses import replace
    paper,_=fixture()
    with pytest.raises(WorkingPaperError,match=reason):
        replace(paper,**{field:value})


def test_reject_unreconciled_engine_categories():
    paper,_=fixture()
    wrong=engine()
    wrong['trace']=[('RULE-ASSET',H,'100'),('RULE-CASHFLOW',H,'30'),('RULE-UNKNOWN',H,'1')]
    with pytest.raises(WorkingPaperError,match='Unmatched'):
        diff(paper,wrong)


def test_reject_bad_rule_trace_hash_and_approval_digest():
    paper,_=fixture()
    wrong=engine()
    wrong['trace']=[('RULE-ASSET','invalid','100')]
    with pytest.raises(WorkingPaperError,match='Invalid engine'):
        diff(paper,wrong)


def test_reject_invalid_json_and_excessively_large_paper():
    bad=b'not a json document'
    with pytest.raises(WorkingPaperError,match='Invalid, noncanonical'):
        parse_working_paper_bytes(bad,expected_sha256=hashlib.sha256(bad).hexdigest(),
            approved_ref='test',bank_approved_sha256=H,synthetic_only=True)
    with pytest.raises(WorkingPaperError,match='size'):
        parse_working_paper_bytes(b'x'*2_000_001,expected_sha256=H,
            approved_ref='test',bank_approved_sha256=H,synthetic_only=True)


def test_reject_missing_exact_paper_fields_and_negative_metric():
    from dataclasses import replace
    paper,_=fixture()
    with pytest.raises(WorkingPaperError,match='nonnegative'):
        replace(paper,measures={**paper.measures,'hqla':Decimal('-1')})
    with pytest.raises(ValueError,match='NaN'):
        replace(paper,rule_amounts={'RULE-X':Decimal('NaN')})


def test_reject_no_trace_or_missing_metric_and_undocumented_ratio_delta():
    paper,_=fixture()
    wrong=engine()
    del wrong['lcr']
    with pytest.raises(WorkingPaperError,match='mandatory trace'):
        diff(paper,wrong)
    wrong=engine()
    wrong['lcr']=Decimal('2.5')
    assert diff(paper,wrong).status=='FAILED'