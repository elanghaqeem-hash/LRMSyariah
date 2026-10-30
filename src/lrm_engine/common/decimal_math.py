"""Validated Decimal-only input and output; rule: ENG-DEC-001.

Legal basis: model integrity engineering control; NOT a regulatory factor.
"""
from __future__ import annotations

from decimal import (
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    localcontext,
)
from typing import TypeAlias

DecimalInput: TypeAlias = Decimal | str | int
ENGINE_CONTEXT = Context(prec=38, rounding=ROUND_HALF_EVEN)
for _signal in (DivisionByZero, InvalidOperation, Overflow):
    ENGINE_CONTEXT.traps[_signal] = True


def as_decimal(value: DecimalInput) -> Decimal:
    """Parse exact decimal input; reject bool, floats, NaN and Infinity."""
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError("binary floats and booleans are forbidden for values/factors")
    if not isinstance(value, (Decimal, str, int)):
        raise TypeError("expected Decimal, integer or exact decimal string")
    if isinstance(value, str) and not value.strip():
        raise ValueError("empty decimal string")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid decimal input") from exc
    if not result.is_finite():
        raise ValueError("NaN and Infinity are forbidden")
    return result


def decimal_plain(value: Decimal) -> str:
    """Canonical non-exponent string with no representational trailing zeros."""
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError("expected finite Decimal")
    if value.is_zero():
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    """Unrounded exact-precision ratio, explicit divide-by-zero failure."""
    numerator = as_decimal(numerator)
    denominator = as_decimal(denominator)
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    with localcontext(ENGINE_CONTEXT):
        return numerator / denominator


def round_for_output(value: Decimal, *, places: int, rounding: str = ROUND_HALF_EVEN) -> Decimal:
    """Round ONLY at presentation boundary; caller supplies report precision."""
    if places < 0 or places > 18:
        raise ValueError("places outside supported output policy [0, 18]")
    value = as_decimal(value)
    quantum = Decimal(1).scaleb(-places)
    with localcontext(ENGINE_CONTEXT) as ctx:
        ctx.rounding = rounding
        return value.quantize(quantum)
