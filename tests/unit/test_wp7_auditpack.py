"""Synthetic output evidence: deterministic audit ZIP, never raw banking data."""
from dataclasses import replace
import io
import hashlib
import json
import zipfile
import pytest

from lrm_engine.common.canonical import canonical_json
from lrm_reporting.auditpack import ApprovedRunEvidence, make_audit_pack


def test_deterministic_audit_pack():
    result={'lcr': '1.28'}
    sha=hashlib.sha256(canonical_json(result)).hexdigest()
    r=ApprovedRunEvidence('run-fixture','2026-10-30','LCR_DAILY','a'*64,'b'*64,sha,
                           '0.4.0+deadbeef','map-v4','param-v4','maker','checker','2026-10-30T00:00:00Z')
    kw={'run':r,'dq_summary':{'status':'PASS'},'reconciliation':{'status':'PASS'},
        'result':result,'trace':{'sha':'c'*64}}
    a=make_audit_pack(**kw)
    assert a==make_audit_pack(**kw)
    with zipfile.ZipFile(io.BytesIO(a)) as z:
        assert len(z.namelist())==6
        m=json.loads(z.read('manifest.json'))
        assert m['regulatory_filing_approved'] is False
        assert m['file_sha256']['result.json']==sha
    with pytest.raises(ValueError,match='independently approved'):
        make_audit_pack(**{**kw,'run':replace(r,checker_id='maker')})
    with pytest.raises(ValueError,match='must both pass'):
        make_audit_pack(**{**kw,'dq_summary':{'status':'WARNING'}})
    with pytest.raises(ValueError,match='result hash'):
        make_audit_pack(**{**kw,'result':{'lcr':'2'}})