"""WP11 funding-concentration summary for ILAAP, SEOJK 26/2025 [VERIFY].

Only pseudonymous depositor keys are accepted; no actual account/customer names.
Funding concentration is support data, not a regulatory judgement.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Sequence

from lrm_engine.common.decimal_math import ENGINE_CONTEXT, as_decimal, ratio


@dataclass(frozen=True)
class FundingBalance:
    pseudonymous_group: str
    akad: str
    balance: Decimal

    def __post_init__(self) -> None:
        v = as_decimal(self.balance)
        if not self.pseudonymous_group.startswith('MASK_') or not self.akad.strip() or v < 0:
            raise ValueError('Only nonnegative pseudonymous funding positions accepted')
        object.__setattr__(self, 'balance', v)


@dataclass(frozen=True)
class ConcentrationReport:
    total: Decimal
    top_n: int
    top_n_amount: Decimal
    top_n_share: Decimal
    group_count: int
    methodology_status: str = 'ENGINEERING_UNVERIFIED'


def funding_concentration(balances: Sequence[FundingBalance], *, top_n: int) -> ConcentrationReport:
    """Combine balances for the same pseudonymous depositor before ranking."""
    if isinstance(top_n,bool) or not isinstance(top_n,int) or top_n <= 0:
        raise ValueError('Top-N must be positive integer')
    grouped: dict[str,Decimal] = {}
    with localcontext(ENGINE_CONTEXT):
        for row in balances:
            grouped[row.pseudonymous_group] = grouped.get(row.pseudonymous_group, Decimal(0)) + row.balance
        total=sum(grouped.values(),Decimal(0))
        ranked=sorted(grouped.values(), reverse=True)
        top_amount=sum(ranked[:top_n],Decimal(0))
        return ConcentrationReport(total,top_n,top_amount,ratio(top_amount,total),len(grouped))