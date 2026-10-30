"""Engineering-only simulation fixtures, not prescribed OJK factors."""
import pytest
from decimal import Decimal, localcontext
from lrm_engine.common.decimal_math import ENGINE_CONTEXT
from lrm_engine.nsfr.calculator import NSFRFactor,NSFRLeg,calculate_nsfr
from lrm_engine.common.time_buckets import TimeBucket
from lrm_engine.survival.ladder import DatedCashFlow,calculate_survival
from lrm_engine.dcr.monitor import calculate_dcr

SHA='b'*64


def factor(v):
    return NSFRFactor(Decimal(v),'Synthetic reference','TEST-RULE',
                      'approved-fixture','SYNTHETIC-ONLY')


def leg(v):
    return NSFRLeg(v,'mudharabah','test','>1y','testfactor','NSFR-SYN',SHA)


def test_nsfr_golden():
    r=calculate_nsfr(funding=[leg('200')],assets=[leg('125')],
                     factors={'ASF.testfactor':factor('.8'),'RSF.testfactor':factor('.5')})
    assert r.available_stable_funding==Decimal('160')
    assert r.required_stable_funding==Decimal('62.5')
    assert r.nsfr==Decimal('2.56')


def test_missing_funding_factor_rejected():
    with pytest.raises(ValueError,match='Missing approved'):
        calculate_nsfr(funding=[leg('100')],assets=[leg('100')],factors={'RSF.testfactor':factor('.5')})


def test_nsfr_zero_rsf_denied():
    with pytest.raises(ValueError,match='denominator'):
        calculate_nsfr(funding=[leg('100')],assets=[],factors={'ASF.testfactor':factor('.8')})


def test_survival_19_buckets_breach():
    buckets=[TimeBucket('D'+str(i),i,i) for i in range(19)]
    r=calculate_survival(opening_buffer='100',cashflows=[DatedCashFlow(2,'0','110')],
                         buckets=buckets,tolerance='0')
    assert r.critical_bucket=='D2'
    assert r.survival_days==2
    assert r.steps[2].cumulative_position==Decimal('-10')


def test_survival_no_breach():
    buckets=[TimeBucket('A',0,1)]
    r=calculate_survival(opening_buffer='100',cashflows=[DatedCashFlow(1,'10','20')],
                         buckets=buckets,tolerance='0',require_nineteen=False)
    assert not r.breach and r.survival_days is None


def test_survival_requires_approved_bucket_count():
    with pytest.raises(ValueError,match='19'):
        calculate_survival(opening_buffer='100',cashflows=[],buckets=[TimeBucket('A',0,None)],tolerance='0')


def test_dcr_rate_gap_scenario():
    r=calculate_dcr(mudharabah_balance='1000',benchmark_rate='.06',equivalent_rate='.04',
                    tolerance='.005',beta='.5',target_rate='.05',
                    distributable_rate='.04',time_days=30,day_count_basis='365')
    assert r.rate_gap==Decimal('.02')
    assert r.additional_runoff==Decimal('7.5')
    with localcontext(ENGINE_CONTEXT):
        assert r.smoothing_cost==Decimal('10')*Decimal(30)/Decimal(365)
    assert r.warning


def test_dcr_zero_gap():
    r=calculate_dcr(mudharabah_balance='1000',benchmark_rate='.04',equivalent_rate='.06',
                    tolerance='.005',beta='.5',target_rate='.04',
                    distributable_rate='.05',time_days=30,day_count_basis='365')
    assert r.additional_runoff==0 and r.smoothing_cost==0 and not r.warning


def test_dcr_float_refused():
    with pytest.raises(TypeError):
        calculate_dcr(mudharabah_balance=1.0,benchmark_rate='0',equivalent_rate='0',
                    tolerance='0',beta='0',target_rate='0',distributable_rate='0',
                    time_days=1,day_count_basis='365')