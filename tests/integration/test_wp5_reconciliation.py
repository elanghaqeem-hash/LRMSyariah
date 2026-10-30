"""Synthetic WP5 reconciliation controls. Numeric examples are not Bank data."""
from decimal import Decimal
import pytest

from lrm_data.reconciliation import ReconEntry as E, ReconPolicy, reconcile_three_layers


def p(tol='0'):
    return ReconPolicy(Decimal(tol), approval_ref='SYNTHETIC-CHECKER',
                       legal_basis='Bank policy synthetic test only', parameter_version='v-test')


def r(bank, detail, engine, tol='0'):
    return reconcile_three_layers(bank_gl=bank, source_detail=detail,
                                  engine_output=engine, policy=p(tol))


def test_three_layer_pass():
    gl=[E('A','300','2026-10-30'), E('B','-80','2026-10-30')]
    detail=[E('B','-80','2026-10-30'), E('A','200','2026-10-30'), E('A','100','2026-10-30')]
    engine=[E('A','300','2026-10-30'), E('B','-80','2026-10-30')]
    result=r(gl,detail,engine)
    assert result.status == 'PASS'
    assert len(result.lines)==2
    assert all(x.source_variance == 0 and x.engine_variance == 0 for x in result.lines)


def test_tolerance_applied_to_both_layers():
    report=r([E('A','100','d')],[E('A','100.25','d')],[E('A','100.49','d')],'.25')
    assert report.status=='PASS'
    assert report.lines[0].source_variance==Decimal('.25')


def test_unexplained_difference_blocks():
    report=r([E('A','100','d')],[E('A','100.26','d')],[E('A','100.30','d')],'.25')
    assert report.status=='FAILED'


def test_missing_gl_blocks():
    with pytest.raises(ValueError,match='coverage mismatch'):
        r([E('A','1','d'),E('B','2','d')],[E('A','1','d')],[E('A','1','d')])


def test_duplicate_anchor_blocks():
    with pytest.raises(ValueError,match='Duplicate'):
        r([E('A','1','d'),E('A','2','d')],[E('A','3','d')],[E('A','3','d')])


def test_cross_date_blocks():
    with pytest.raises(ValueError,match='Mixed reporting dates'):
        r([E('A','1','d1')],[E('A','1','d2')],[E('A','1','d1')])


def test_no_zero_implicit_layer():
    with pytest.raises(ValueError,match='three populated'):
        r([E('A','1','d')],[],[E('A','1','d')])


def test_unverified_or_negative_policy_blocks():
    with pytest.raises(ValueError):
        p('-0.1')
    with pytest.raises(ValueError):
        ReconPolicy('0','[VERIFY]','base','v1')


def test_float_rejected():
    with pytest.raises(TypeError):
        E('A',1.0,'2026')