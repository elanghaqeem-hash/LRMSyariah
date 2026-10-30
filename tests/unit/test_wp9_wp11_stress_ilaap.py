"""Synthetic stress / ILAAP analytic tests; not external regulatory assumptions."""
import pytest
from decimal import Decimal, localcontext
from lrm_engine.common.decimal_math import ENGINE_CONTEXT
from lrm_engine.stress.scenario import StressScenario,stressed_lcr
from lrm_engine.lcr.calculator import Factor, HQLALeg, RegulatoryLeg
from lrm_engine.ilaap.funding import FundingBalance, funding_concentration

H='c'*64

def f(v):
    return Factor(Decimal(v),'TEST','Synthetic rule','v-fixture','SYNTHETIC-ONLY')

def factors():
    return {'hqlacap.level2':f('.4'),'hqlacap.level2b':f('.15'),
            'haircut.test':f('0'),'out.test':f('1'),
            'in.test':f('1'),'inflow.cap':f('.75')}

def scenario():
    return StressScenario('synthetic','v1','SYNTHETIC-CHECKER','0.8','1.5','0.5')

def test_stress_lcr_reduces_ratio():
    h=[HQLALeg('100','w','HQLA',H,'haircut.test','L1')]
    out=[RegulatoryLeg('50','m','O',H,'out.test')]
    inc=[RegulatoryLeg('10','m','I',H,'in.test')]
    r=stressed_lcr(scenario=scenario(),hqla=h,outflows=out,inflows=inc,
                   factors=factors(),has_unwind_transactions=False)
    assert r.hqla==Decimal('80')
    assert r.outflow==Decimal('75')
    assert r.inflow_raw==Decimal('5')
    with localcontext(ENGINE_CONTEXT):
        assert r.lcr==Decimal(80)/Decimal(70)

def test_missing_scenario_approval_ref():
    with pytest.raises(ValueError):
        StressScenario('x','v1','[VERIFY]','1','1','1')

def test_invalid_stress_shock():
    with pytest.raises(ValueError):
        StressScenario('x','v1','checker','1.1','1','1')

def test_concentration_aggregates_multiple_products():
    x=[FundingBalance('MASK_A','mudharabah','70'),
       FundingBalance('MASK_A','wadiah','30'),
       FundingBalance('MASK_B','mudharabah','60')]
    r=funding_concentration(x,top_n=1)
    assert r.total==Decimal('160')
    assert r.top_n_amount==Decimal('100')
    assert r.top_n_share==Decimal('0.625')
    assert r.group_count==2

def test_raw_customer_names_disallowed():
    with pytest.raises(ValueError):
        FundingBalance('name','wadiah','100')

def test_top_n_and_zero_funding_fail():
    with pytest.raises(ValueError):
        funding_concentration([FundingBalance('MASK_A','w','1')],top_n=0)
    with pytest.raises(ValueError,match='denominator'):
        funding_concentration([],top_n=50)