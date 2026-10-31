"""30-day Islamic SFT/repo collateral unwind; POJK 20/2025 Lampiran I III.C.3-7.

This is a governed *calculation primitive*, not certification of legal
eligibility, collateral ownership, security pricing, contract validity or
cash-flow offset. Bank-approved extracts and independent checks are required.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, localcontext
from typing import Any, Mapping

from lrm_engine.common.canonical import sha256_canonical
from lrm_engine.common.decimal_math import ENGINE_CONTEXT, as_decimal

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_TOKEN = re.compile(r"(?:SFT|ASSET|LEG)-[A-Za-z0-9_-]{8,72}\Z")
_LEVELS = ("L1", "L2A", "L2B")


class SFTLedgerError(ValueError):
    """Safe non-customer-specific refusal of incomplete collateral evidence."""


def _sha(value: str, name: str) -> None:
    if not _SHA.fullmatch(value):
        raise SFTLedgerError(f"{name} requires a SHA-256 digest")


def _reference(value: str, name: str) -> None:
    if not value or not value.strip() or any(q in value.upper() for q in ("TBD", "[VERIFY]")):
        raise SFTLedgerError(f"{name} must be an independently recorded reference")


@dataclass(frozen=True)
class UnwindLeg:
    """One *unique* asset parcel/cash leg when a settled SFT is reversed.

    RETURN_FROM_COUNTERPARTY is an asset newly available to the Bank at
    unwind, not in reporting-date HQLA stock. RETURN_TO_COUNTERPARTY is in
    reporting-date stock and leaves the Bank at unwind. Both values are
    post-haircut; no haircut is applied a second time.
    """

    leg_id: str
    asset_id: str
    level: str
    movement: str
    post_haircut_value: Decimal
    counted_in_current_stock: bool
    security_eligibility_ref: str
    independent_price_ref: str
    custody_encumbrance_ref: str
    source_sha256: str

    def __post_init__(self) -> None:
        if not _TOKEN.fullmatch(self.leg_id) or not _TOKEN.fullmatch(self.asset_id):
            raise SFTLedgerError("Only pseudonymized leg and asset parcel tokens are permitted")
        if self.level not in _LEVELS:
            raise SFTLedgerError("Every SFT leg requires an approved HQLA level")
        if self.movement not in ("RETURN_FROM_COUNTERPARTY", "RETURN_TO_COUNTERPARTY"):
            raise SFTLedgerError("Unknown SFT unwind direction")
        if type(self.counted_in_current_stock) is not bool:
            raise SFTLedgerError("Stock membership must be an explicit boolean")
        if self.counted_in_current_stock != (self.movement == "RETURN_TO_COUNTERPARTY"):
            raise SFTLedgerError("Unwind asset would be double-counted against reporting-date HQLA")
        amount = as_decimal(self.post_haircut_value)
        if not amount.is_finite() or amount <= 0:
            raise SFTLedgerError("Unwind amount must be finite and positive")
        for label, value in (("eligibility", self.security_eligibility_ref),
                             ("price", self.independent_price_ref),
                             ("custody", self.custody_encumbrance_ref)):
            _reference(value, label)
        _sha(self.source_sha256, "leg source")
        object.__setattr__(self, "post_haircut_value", amount)


@dataclass(frozen=True)
class SFTTrade:
    trade_id: str
    trade_kind: str
    akad: str
    trade_date: date
    settlement_date: date
    maturity_date: date
    currency: str
    state: str
    signed_contract_sha256: str
    settlement_sha256: str
    legal_sharia_ref: str
    legs: tuple[UnwindLeg, ...]

    def __post_init__(self) -> None:
        if not _TOKEN.fullmatch(self.trade_id):
            raise SFTLedgerError("Trade identifier must be pseudonymized")
        if self.trade_kind not in ("REPO_SYARIAH", "REVERSE_REPO_SYARIAH", "COLLATERAL_SWAP"):
            raise SFTLedgerError("Unrecognized secured Islamic transaction type")
        _reference(self.akad, "akad")
        _reference(self.legal_sharia_ref, "sharia contract review")
        if self.state != "SETTLED_OPEN":
            raise SFTLedgerError("Only confirmed settled and outstanding SFT may enter ledger")
        if self.trade_date > self.settlement_date or self.settlement_date >= self.maturity_date:
            raise SFTLedgerError("Invalid SFT settlement/maturity sequence")
        if not re.fullmatch(r"[A-Z]{3}", self.currency):
            raise SFTLedgerError("ISO currency must be supplied")
        _sha(self.signed_contract_sha256, "contract")
        _sha(self.settlement_sha256, "settlement")
        if len(self.legs) < 2:
            raise SFTLedgerError("An SFT must contain both legs of the collateral exchange")
        dirs = {leg.movement for leg in self.legs}
        if dirs != {"RETURN_FROM_COUNTERPARTY", "RETURN_TO_COUNTERPARTY"}:
            raise SFTLedgerError("A balanced collateral exchange requires both unwind directions")
        if len({leg.leg_id for leg in self.legs}) != len(self.legs):
            raise SFTLedgerError("Duplicated SFT leg identifier")
        if len({leg.asset_id for leg in self.legs}) != len(self.legs):
            raise SFTLedgerError("An SFT asset parcel cannot appear twice in an exchange")


@dataclass(frozen=True)
class SFTLedger:
    reporting_date: date
    reporting_currency: str
    source_batch_sha256: str
    hqla_stock_sha256: str
    bank_sft_policy_ref: str
    bank_sft_policy_sha256: str
    trades: tuple[SFTTrade, ...]

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Z]{3}", self.reporting_currency):
            raise SFTLedgerError("Invalid SFT reporting currency")
        _sha(self.source_batch_sha256, "SFT extract")
        _sha(self.hqla_stock_sha256, "HQLA stock")
        _sha(self.bank_sft_policy_sha256, "Bank SFT policy")
        _reference(self.bank_sft_policy_ref, "Bank SFT policy")
        if not self.trades:
            raise SFTLedgerError("Nonempty SFT transaction ledger required")
        if len({t.trade_id for t in self.trades}) != len(self.trades):
            raise SFTLedgerError("Duplicate trade in SFT batch")
        assets: set[str] = set()
        for trade in self.trades:
            if trade.currency != self.reporting_currency:
                raise SFTLedgerError("FX conversion is not approved for SFT in this currency")
            if trade.settlement_date > self.reporting_date or trade.maturity_date <= self.reporting_date:
                raise SFTLedgerError("SFT is not an outstanding settled position at reporting date")
            for leg in trade.legs:
                if leg.asset_id in assets:
                    raise SFTLedgerError("Collateral or cash parcel reused across SFT transactions")
                assets.add(leg.asset_id)


@dataclass(frozen=True)
class AdjustedHQLA:
    level1: Decimal
    level2a: Decimal
    level2b: Decimal
    eligible_trades: int
    excluded_long_dated_trades: int
    ledger_sha256: str
    trace: tuple[tuple[str, str, Decimal], ...]


def stock_fingerprint(levels: Mapping[str, Decimal]) -> str:
    """Tie the ledger to current post-haircut engine HQLA stock before caps."""
    if set(levels) != set(_LEVELS):
        raise SFTLedgerError("Complete reporting-date HQLA stock is mandatory")
    return sha256_canonical({level: as_decimal(levels[level]) for level in _LEVELS})


def adjust_hqla_for_sft(*, current: Mapping[str, Decimal], ledger: SFTLedger,
                        reporting_date: date, currency: str) -> AdjustedHQLA:
    """Apply only settled exchanges whose contractual maturity is <= 30 days.

    Incoming assets are added once and outgoing assets are removed once;
    anything unknown/partial fails closed rather than assuming zero unwind.
    """
    if reporting_date != ledger.reporting_date or currency != ledger.reporting_currency:
        raise SFTLedgerError("SFT ledger cut-off and currency differ from LCR run")
    if stock_fingerprint(current) != ledger.hqla_stock_sha256:
        raise SFTLedgerError("SFT ledger not reconciled to the original HQLA stock")
    with localcontext(ENGINE_CONTEXT):
        adjusted = {level: as_decimal(current[level]) for level in _LEVELS}
        if any(v < 0 for v in adjusted.values()):
            raise SFTLedgerError("Original HQLA level cannot be negative")
        removed = {level: Decimal(0) for level in _LEVELS}
        included = 0
        excluded = 0
        events: list[tuple[str, str, Decimal]] = []
        for trade in sorted(ledger.trades, key=lambda t: t.trade_id):
            if trade.maturity_date > reporting_date + timedelta(days=30):
                excluded += 1
                continue
            included += 1
            for leg in sorted(trade.legs, key=lambda t: t.leg_id):
                delta = leg.post_haircut_value
                if leg.movement == "RETURN_TO_COUNTERPARTY":
                    removed[leg.level] += delta
                    delta = -delta
                adjusted[leg.level] += delta
                events.append((trade.trade_id, leg.level, delta))
        if not included:
            raise SFTLedgerError("No eligible short-term SFT exists; inconsistent unwind declaration")
        if any(removed[level] > as_decimal(current[level]) for level in _LEVELS):
            raise SFTLedgerError("Unwind removes more HQLA than included in current stock")
        if any(v < 0 for v in adjusted.values()):
            raise SFTLedgerError("Negative adjusted HQLA after collateral unwind")
        return AdjustedHQLA(
            level1=adjusted["L1"], level2a=adjusted["L2A"], level2b=adjusted["L2B"],
            eligible_trades=included, excluded_long_dated_trades=excluded,
            ledger_sha256=sha256_canonical(ledger), trace=tuple(events),
        )


def ledger_from_snapshot(value: Mapping[str, Any]) -> SFTLedger:
    """Restore every required governed field from canonical WP3 snapshots."""
    try:
        trades = []
        for row in value["trades"]:
            legs = tuple(UnwindLeg(**part) for part in row["legs"])
            trades.append(SFTTrade(
                trade_id=row["trade_id"], trade_kind=row["trade_kind"], akad=row["akad"],
                trade_date=date.fromisoformat(row["trade_date"]),
                settlement_date=date.fromisoformat(row["settlement_date"]),
                maturity_date=date.fromisoformat(row["maturity_date"]),
                currency=row["currency"], state=row["state"],
                signed_contract_sha256=row["signed_contract_sha256"],
                settlement_sha256=row["settlement_sha256"],
                legal_sharia_ref=row["legal_sharia_ref"], legs=legs))
        return SFTLedger(reporting_date=date.fromisoformat(value["reporting_date"]),
            reporting_currency=value["reporting_currency"],
            source_batch_sha256=value["source_batch_sha256"],
            hqla_stock_sha256=value["hqla_stock_sha256"],
            bank_sft_policy_ref=value["bank_sft_policy_ref"],
            bank_sft_policy_sha256=value["bank_sft_policy_sha256"],trades=tuple(trades))
    except (KeyError, TypeError, ValueError) as exc:
        raise SFTLedgerError("Invalid or incomplete governed SFT snapshot") from exc