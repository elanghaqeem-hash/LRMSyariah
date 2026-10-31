"""Annex I III.C deterministic mathematical tests, synthetic stock only."""
from decimal import Decimal, localcontext
from lrm_engine.common.decimal_math import ENGINE_CONTEXT
import pytest
from lrm_engine.lcr.ojk_annex_caps import official_cap_adjustments as cap

D = Decimal


def no_unwind(l1: str, a: str, b: str):
    return cap(level1=D(l1), level2a=D(a), level2b=D(b),
               adjusted_level1=D(l1), adjusted_level2a=D(a), adjusted_level2b=D(b))


def test_level1_only_uncapped():
    r = no_unwind('100', '0', '0')
    assert r.total_hqla == D('100')
    assert r.deduction_level2 == r.deduction_level2b == 0


def test_level2b_cap_annex_exact():
    r = no_unwind('100', '0', '100')
    with localcontext(ENGINE_CONTEXT):
        assert r.deduction_level2b == D('100') - D(15)/D(85)*D(100)
    assert r.deduction_level2 == 0
    assert abs(r.included_level2b/r.total_hqla - D('0.15')) < D('1e-25')


def test_level2_combined_cap_annex_exact():
    r = no_unwind('100', '100', '100')
    assert r.deduction_level2b == D('75')
    with localcontext(ENGINE_CONTEXT):
        assert r.deduction_level2 == D('100')+D('100')-D('75')-D(2)/D(3)*D('100')
    assert abs((r.included_level2a+r.included_level2b)/r.total_hqla - D('0.4')) < D('1e-25')


def test_mixed_level2a_and_level2b_without_binding():
    r = no_unwind('100', '20', '40')
    assert r.deduction_level2 == 0
    assert abs(r.included_level2b/r.total_hqla - D('0.15')) < D('1e-25')


def test_adjusted_sft_values_are_distinct_from_stock():
    r = cap(level1=D('100'),level2a=D('20'),level2b=D('60'),
            adjusted_level1=D('80'),adjusted_level2a=D('40'),adjusted_level2b=D('40'))
    with localcontext(ENGINE_CONTEXT):
        assert r.deduction_level2b == max(D(40)-D(15)/D(85)*D(120),D(40)-D(15)/D(60)*D(100),D(0))
    with localcontext(ENGINE_CONTEXT):
        assert r.deduction_level2 == D('80')-r.deduction_level2b-D(2)/D(3)*D(80)
    assert abs(r.total_hqla - (D('180')-r.deduction_level2b-r.deduction_level2)) < D('1e-25')


@pytest.mark.parametrize('value', ['-1', 'NaN', 'Infinity'])
def test_invalid_level_fails_closed(value):
    with pytest.raises((ValueError, TypeError)):
        cap(level1=D(value),level2a=D('0'),level2b=D('0'),
            adjusted_level1=D('0'),adjusted_level2a=D('0'),adjusted_level2b=D('0'))


def test_inconsistent_adjusted_exceeds_stock_rejected():
    with pytest.raises(ValueError, match='exceed eligible stock'):
        cap(level1=D('0'),level2a=D('0'),level2b=D('1'),
            adjusted_level1=D('0'),adjusted_level2a=D('0'),adjusted_level2b=D('100'))