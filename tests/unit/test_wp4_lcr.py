"""WP4 synthetic LCR rule tests. Factor values below are not regulatory claims."""
from decimal import Decimal
from dataclasses import replace
import pytest
from lrm_engine.lcr.calculator import Factor, RegulatoryLeg, HQLALeg, calculate_lcr

H = 'a' * 64

def f(v):
    return Factor(Decimal(v), rule_id='R-TEST', legal_basis='Synthetic banking-methodology fixture',
                  approved_revision='test-approved-v1', verification_ref='SYNTHETIC-TEST-ONLY')

def settings():
    return {'haircut.level1':f('0'), 'haircut.level2a':f('.15'),
            'haircut.level2b':f('.50'), 'hqlacap.level2':f('.4'),
            'hqlacap.level2b':f('.15'), 'outflow.test':f('.10'),
            'inflow.test':f('1'), 'inflow.cap':f('.75')}

def test_golden_simple_all_components():
    holdings=[HQLALeg(Decimal('200'), 'wadiah', 'H1', H, 'haircut.level1', 'L1'),
              HQLALeg(Decimal('100'), 'sukuk', 'H2', H, 'haircut.level2a', 'L2A')]
    withdrawals=[RegulatoryLeg(Decimal('1000'), 'mudharabah', 'O1', H, 'outflow.test')]
    collections=[RegulatoryLeg(Decimal('90'), 'murabahah', 'I1', H, 'inflow.test')]
    r=calculate_lcr(hqla=holdings, outflows=withdrawals,
                  inflows=collections, factors=settings(), has_unwind_transactions=False)
    assert r.level1 == Decimal(200)
    assert r.level2a == Decimal(85)
    assert r.inflow_used == Decimal(75)
    assert r.net_cash_outflow == Decimal(25)
    assert r.lcr == Decimal('11.4')
    assert len(r.trace)==4

def test_level2b_capped_and_level2_total():
    holdings=[HQLALeg('100','w','H1',H,'haircut.level1','L1'),
              HQLALeg('20','s','H2',H,'haircut.level2a','L2A'),
              HQLALeg('100','s','H3',H,'haircut.level2b','L2B')]
    r=calculate_lcr(hqla=holdings, outflows=[RegulatoryLeg('1000','m','O',H,'outflow.test')],
                    inflows=[], factors=settings(), has_unwind_transactions=False)
    assert r.level2b / r.hqla <= Decimal('.15')
    assert (r.level2a + r.level2b)/r.hqla <= Decimal('.4')

def test_missing_factor_fails_loud():
    with pytest.raises(ValueError, match='factor missing'):
        calculate_lcr(hqla=[], outflows=[RegulatoryLeg('10','m','O',H,'no-such-factor')],
                      inflows=[],factors=settings(),has_unwind_transactions=False)

def test_unwind_cannot_be_silently_ignored():
    with pytest.raises(ValueError, match='unwind'):
        calculate_lcr(hqla=[],outflows=[],inflows=[],factors=settings(),
                      has_unwind_transactions=True)

def test_nonfinite_and_unverified_factors_rejected():
    with pytest.raises((ValueError,TypeError)):
        f('NaN')
    with pytest.raises(ValueError):
        Factor(Decimal('.1'),'r','[VERIFY]','v','e')
    with pytest.raises(ValueError):
        Factor(Decimal('.1'),'r','verified','v','e',status='DRAFT_UNVERIFIED')

def test_source_must_be_hashed_and_akad_present():
    with pytest.raises(ValueError):
        RegulatoryLeg('30','','O',H,'outflow.test')
    with pytest.raises(ValueError):
        RegulatoryLeg('30','m','O','no','outflow.test')
    with pytest.raises(ValueError):
        RegulatoryLeg('-1','m','O',H,'outflow.test')

def test_hqla_l1_monotonic():
    x=RegulatoryLeg('1000','m','O',H,'outflow.test')
    h=HQLALeg('100','w','H1',H,'haircut.level1','L1')
    a=calculate_lcr(hqla=[h],outflows=[x],inflows=[],factors=settings(),has_unwind_transactions=False)
    b=calculate_lcr(hqla=[replace(h,amount='200')],outflows=[x],inflows=[],factors=settings(),has_unwind_transactions=False)
    assert b.lcr >= a.lcr

def test_zero_nco_fails():
    with pytest.raises(ValueError, match='denominator'):
        calculate_lcr(hqla=[],outflows=[],inflows=[],factors=settings(),has_unwind_transactions=False)

def test_reorder_invariance():
    h=[HQLALeg('100','w','H1',H,'haircut.level1','L1'),HQLALeg('30','s','H2',H,'haircut.level2a','L2A')]
    out=[RegulatoryLeg('1000','m','O1',H,'outflow.test'),RegulatoryLeg('500','m','O2',H,'outflow.test')]
    a=calculate_lcr(hqla=h,outflows=out,inflows=[],factors=settings(),has_unwind_transactions=False)
    b=calculate_lcr(hqla=list(reversed(h)),outflows=list(reversed(out)),inflows=[],factors=settings(),has_unwind_transactions=False)
    assert a.lcr == b.lcr