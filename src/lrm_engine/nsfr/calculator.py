"""WP8 engineering ASF/RSF calculator (R05), POJK 20/2025 [VERIFY].

No default maturity weights or factors. Classification by akad, counterparty,
encumbrance and remaining tenor must be supplied by approved bank mapping.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Mapping, Sequence
import re

from lrm_engine.common.decimal_math import ENGINE_CONTEXT, as_decimal, ratio


@dataclass(frozen=True)
class NSFRFactor:
    value: Decimal
    legal_basis: str
    rule_id: str
    approved_revision: str
    verification_ref: str
    status: str = 'ACTIVE'

    def __post_init__(self) -> None:
        v = as_decimal(self.value)
        if not Decimal(0) <= v <= Decimal(1) or self.status != 'ACTIVE':
            raise ValueError('Unapproved or out-of-range ASF/RSF factor')
        if any(not x.strip() or '[VERIFY]' in x.upper() or 'TBD' in x.upper()
               for x in (self.legal_basis,self.rule_id,self.approved_revision,self.verification_ref)):
            raise ValueError('Missing verified NSFR rule provenance')
        object.__setattr__(self, 'value', v)


@dataclass(frozen=True)
class NSFRLeg:
    amount: Decimal
    akad: str
    category: str
    maturity_bucket: str
    factor_key: str
    rule_id: str
    source_sha256: str

    def __post_init__(self) -> None:
        v = as_decimal(self.amount)
        if v < 0 or any(not str(x).strip() for x in (
             self.akad,self.category,self.maturity_bucket,self.factor_key,self.rule_id)):
            raise ValueError('Invalid source classification or negative amount')
        if not re.fullmatch('[0-9a-f]{64}', self.source_sha256):
            raise ValueError('Source SHA256 required')
        object.__setattr__(self, 'amount', v)


@dataclass(frozen=True)
class NSFRResult:
    available_stable_funding: Decimal
    required_stable_funding: Decimal
    nsfr: Decimal
    trace: tuple[tuple[str, str, Decimal], ...]
    methodology_status: str = 'ENGINEERING_UNVERIFIED'


def calculate_nsfr(*, funding: Sequence[NSFRLeg], assets: Sequence[NSFRLeg],
                   factors: Mapping[str, NSFRFactor]) -> NSFRResult:
    """Pre-classified ASF and RSF contributions, never infer missing policy."""
    with localcontext(ENGINE_CONTEXT):
        af, rf = Decimal(0), Decimal(0)
        trace: list[tuple[str,str,Decimal]] = []
        for side, items in (('ASF', funding), ('RSF', assets)):
            for item in items:
                key = f'{side}.{item.factor_key}'
                factor = factors.get(key)
                if factor is None or factor.status != 'ACTIVE':
                    raise ValueError(f'Missing approved NSFR factor: {key}')
                contribution = item.amount * factor.value
                if side == 'ASF':
                    af += contribution
                else:
                    rf += contribution
                trace.append((item.rule_id,item.source_sha256,contribution))
        return NSFRResult(af, rf, ratio(af,rf), tuple(trace))