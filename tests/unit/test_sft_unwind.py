"""Regulatory SFT unwind movement constraints using fully synthetic transactions."""
from datetime import date, timedelta
from decimal import Decimal
from dataclasses import replace

import pytest

from lrm_engine.lcr.sft_ledger import (
    SFTLedger, SFTTrade, UnwindLeg, SFTLedgerError, adjust_hqla_for_sft,
    stock_fingerprint, ledger_from_snapshot,
)
from lrm_engine.common.canonical import canonical_json
import json

ASOF = date(2026, 10, 31)
SHA = "f" * 64
STOCK = {"L1": Decimal("100"), "L2A": Decimal("40"), "L2B": Decimal("20")}


def leg(num: str, asset: str, level: str, movement: str, amount: str) -> UnwindLeg:
    return UnwindLeg(leg_id="LEG-" + num, asset_id="ASSET-" + asset, level=level,
        movement=movement, post_haircut_value=Decimal(amount),
        counted_in_current_stock=(movement == "RETURN_TO_COUNTERPARTY"),
        security_eligibility_ref="synthetic-eligibility", independent_price_ref="synthetic-price",
        custody_encumbrance_ref="synthetic-custody", source_sha256=SHA)


def trade(days: int = 15, suffix: str = "aaaaaaaa") -> SFTTrade:
    return SFTTrade(trade_id="SFT-" + suffix, trade_kind="REPO_SYARIAH", akad="wakalah",
        trade_date=ASOF - timedelta(days=10), settlement_date=ASOF - timedelta(days=9),
        maturity_date=ASOF + timedelta(days=days), currency="IDR", state="SETTLED_OPEN",
        signed_contract_sha256=SHA, settlement_sha256=SHA,
        legal_sharia_ref="synthetic-DPS-case", legs=(
           leg(suffix+"01", suffix+"11", "L1", "RETURN_TO_COUNTERPARTY", "30"),
           leg(suffix+"02", suffix+"12", "L2A", "RETURN_FROM_COUNTERPARTY", "20")))


def ledger(*trades: SFTTrade) -> SFTLedger:
    return SFTLedger(reporting_date=ASOF, reporting_currency="IDR", source_batch_sha256=SHA,
        hqla_stock_sha256=stock_fingerprint(STOCK), bank_sft_policy_ref="synthetic-policy-01",
        bank_sft_policy_sha256=SHA, trades=tuple(trades))


def test_repo_collateral_unwind_exact_and_30_day():
    result = adjust_hqla_for_sft(current=STOCK, ledger=ledger(trade(days=30)),
                                  reporting_date=ASOF, currency="IDR")
    assert (result.level1, result.level2a, result.level2b) == (Decimal(70), Decimal(60), Decimal(20))
    assert result.eligible_trades == 1 and result.excluded_long_dated_trades == 0
    assert len(result.trace) == 2


def test_long_dated_is_excluded_but_never_unwound():
    result = adjust_hqla_for_sft(current=STOCK,
        ledger=ledger(trade(days=31,suffix="bbbbbbbb"),trade(days=30,suffix="aaaaaaaa")),
        reporting_date=ASOF, currency="IDR")
    assert result.excluded_long_dated_trades == 1 and result.eligible_trades == 1
    assert result.level1 == 70


def test_no_in_scope_sft_fails_closed():
    with pytest.raises(SFTLedgerError,match="No eligible short-term"):
        adjust_hqla_for_sft(current=STOCK,ledger=ledger(trade(days=31)),
                            reporting_date=ASOF,currency="IDR")


def test_ledger_stock_reconciliation_cannot_be_bypassed():
    with pytest.raises(SFTLedgerError,match="not reconciled"):
        adjust_hqla_for_sft(current={**STOCK,"L1":Decimal(99)},ledger=ledger(trade()),
                            reporting_date=ASOF,currency="IDR")


def test_double_count_stock_membership_blocked():
    with pytest.raises(SFTLedgerError,match="double-counted"):
        replace(trade().legs[1],counted_in_current_stock=True)


def test_same_security_parcel_across_multiple_sft_blocked():
    t1=trade()
    t2=trade(days=18,suffix="bbbbbbbb")
    t2=replace(t2,legs=(replace(t2.legs[0],asset_id=t1.legs[0].asset_id),t2.legs[1]))
    with pytest.raises(SFTLedgerError,match="reused"):
        ledger(t1,t2)


def test_outgoing_cannot_exceed_original_stock():
    t=trade()
    t=replace(t,legs=(replace(t.legs[0],post_haircut_value=Decimal(101)),t.legs[1]))
    with pytest.raises(SFTLedgerError,match="more HQLA"):
        adjust_hqla_for_sft(current=STOCK,ledger=ledger(t),reporting_date=ASOF,currency="IDR")


def test_maturity_or_settlement_inconsistent():
    with pytest.raises(SFTLedgerError,match="not an outstanding"):
        ledger(replace(trade(),maturity_date=ASOF))
    with pytest.raises(SFTLedgerError,match="Invalid SFT settlement"):
        replace(trade(),settlement_date=ASOF+timedelta(days=16))


def test_no_cash_or_collateral_exchange_blocked():
    with pytest.raises(SFTLedgerError,match="both unwind directions"):
        replace(trade(),legs=(trade().legs[0],replace(trade().legs[1],
            movement="RETURN_TO_COUNTERPARTY",counted_in_current_stock=True)))


def test_snapshot_exact_reproduction():
    raw=json.loads(canonical_json(ledger(trade())))
    restored=ledger_from_snapshot(raw)
    assert adjust_hqla_for_sft(current=STOCK,ledger=restored,
               reporting_date=ASOF,currency="IDR").ledger_sha256 == adjust_hqla_for_sft(
               current=STOCK,ledger=ledger(trade()), reporting_date=ASOF,currency="IDR").ledger_sha256


def test_currency_and_missing_source_ref_blocked():
    with pytest.raises(SFTLedgerError,match="FX"):
        ledger(replace(trade(),currency="USD"))
    with pytest.raises(SFTLedgerError,match="requires a SHA"):
        replace(trade().legs[0],source_sha256="unknown")