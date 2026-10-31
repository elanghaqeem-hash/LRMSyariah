"""Pure LCR boundary tests enforcing Annex I composition and factor provenance."""
from decimal import Decimal
import pytest
from lrm_engine.lcr.calculator import Factor, HQLALeg, RegulatoryLeg, calculate_lcr

H = "a" * 64


def factor(value: str) -> Factor:
    return Factor(value=Decimal(value), rule_id="TEST-POJK20", legal_basis="Annex I OJK official reference",
                  approved_revision="SYNTHETIC-MAKER-CHECKER-v1", verification_ref="SYNTHETIC-ONLY")


def config():
    return {
        "hqlacap.level2": factor("0.40"),
        "hqlacap.level2b": factor("0.15"),
        "inflow.cap": factor("0.75"),
        "h1": factor("0"), "h2a": factor("0.15"), "h2b": factor("0.50"),
        "out": factor("0.10"),
    }


def leg(amount: str, level: str, key: str) -> HQLALeg:
    return HQLALeg(amount=Decimal(amount), akad="mudharabah", rule_id="TEST-ASSET",
                   source_sha256=H, factor_key=key, level=level)


def calc(factors):
    return calculate_lcr(hqla=(leg("100", "L1", "h1"),leg("100", "L2A", "h2a"),
                               leg("100", "L2B", "h2b")),
                         outflows=(RegulatoryLeg(amount=Decimal("1000"),akad="wadiah",
                                   rule_id="TEST-O",source_sha256=H,factor_key="out"),),
                         inflows=(), factors=factors, has_unwind_transactions=False)


def test_lcr_uses_annex_deduction_order_no_unwind():
    c = calc(config())
    assert abs(c.hqla - Decimal(100) / Decimal('0.60')) < Decimal('1e-25')
    assert c.level2b == Decimal("25")
    assert abs(c.hqla - (c.level1+c.level2a+c.level2b)) < Decimal('1e-25')


def test_wrong_level2_cap_rejected_even_if_revision_claims_approved():
    factors = config()
    factors["hqlacap.level2"] = factor("0.41")
    with pytest.raises(ValueError, match="Official POJK"):
        calc(factors)


def test_wrong_level2b_cap_rejected():
    factors = config()
    factors["hqlacap.level2b"] = factor("0.20")
    with pytest.raises(ValueError, match="Official POJK"):
        calc(factors)


def test_level1_cannot_be_haircut():
    factors = config()
    factors["h1"] = factor("0.01")
    with pytest.raises(ValueError, match="Level 1"):
        calc(factors)


def test_level2a_must_be_fifteen_percent_haircut():
    factors = config()
    factors["h2a"] = factor("0.10")
    with pytest.raises(ValueError, match="Level 2A"):
        calc(factors)


def test_sft_unwind_still_requires_approved_transaction_ledger():
    with pytest.raises(ValueError, match="unwind"):
        calculate_lcr(hqla=(), outflows=(), inflows=(), factors=config(),
                      has_unwind_transactions=True)