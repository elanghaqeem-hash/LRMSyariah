from decimal import Decimal, ROUND_HALF_UP

import pytest

from lrm_engine.common.decimal_math import (
    as_decimal, decimal_plain, ratio, round_for_output,
)


@pytest.mark.unit
def test_exact_decimal_parsing():
    assert as_decimal("0.10") + as_decimal("0.20") == Decimal("0.30")
    assert as_decimal(5) == Decimal(5)
    assert as_decimal(Decimal("1.25")) == Decimal("1.25")


@pytest.mark.unit
@pytest.mark.parametrize("unsafe", [0.1, True, False, None, [], {}, object()])
def test_reject_non_exact(unsafe):
    with pytest.raises(TypeError):
        as_decimal(unsafe)


@pytest.mark.unit
@pytest.mark.parametrize("unsafe", ["", "  ", "hello", "NaN", "Infinity", "-Infinity"])
def test_reject_invalid(unsafe):
    with pytest.raises(ValueError):
        as_decimal(unsafe)


@pytest.mark.unit
def test_canonical_decimal():
    assert decimal_plain(Decimal("1.23000")) == "1.23"
    assert decimal_plain(Decimal("0E-5")) == "0"
    assert decimal_plain(Decimal("-0.00")) == "0"
    assert decimal_plain(Decimal("1E+3")) == "1000"
    assert decimal_plain(Decimal("123456789012345678901234567890123456789.1200")) == "123456789012345678901234567890123456789.12"
    with pytest.raises(ValueError):
        decimal_plain(Decimal("NaN"))


@pytest.mark.unit
def test_ratio_and_rounding_at_output():
    assert ratio(Decimal(1), Decimal(4)) == Decimal("0.25")
    with pytest.raises(ValueError):
        ratio(Decimal(1), Decimal(0))
    with pytest.raises(ValueError):
        ratio(Decimal(1), Decimal(-1))
    with pytest.raises(TypeError):
        ratio(0.1, Decimal(1))
    assert round_for_output(Decimal("1.235"), places=2) == Decimal("1.24")
    assert round_for_output(Decimal("1.225"), places=2, rounding=ROUND_HALF_UP) == Decimal("1.23")
    with pytest.raises(ValueError):
        round_for_output(Decimal(1), places=-1)
    with pytest.raises(ValueError):
        round_for_output(Decimal(1), places=19)
