"""Test del deprezzamento Ross-Heidecke."""

from __future__ import annotations

import pytest

from brickvalue.domain.enums import ConservationState
from brickvalue.engine.depreciation import compute_depreciation, ross_coefficient


def test_ross_zero_at_age_zero():
    assert ross_coefficient(0, 100) == pytest.approx(0.0)


def test_ross_full_at_end_of_life():
    # Dr = 0.5*(1 + 1) = 1.0
    assert ross_coefficient(100, 100) == pytest.approx(1.0)


def test_ross_midlife():
    # a=0.5 -> 0.5*(0.5 + 0.25) = 0.375
    assert ross_coefficient(50, 100) == pytest.approx(0.375)


def test_new_state_only_age_depreciation():
    # Heidecke 0 per 'nuovo' -> residuo = (1 - Dr)
    res = compute_depreciation(50, 100, ConservationState.NEW)
    assert res.heidecke_coefficient == pytest.approx(0.0)
    assert res.total_depreciation == pytest.approx(0.375, abs=1e-3)
    assert res.residual_ratio == pytest.approx(0.625, abs=1e-3)


def test_combined_formula():
    # total = Dr + C*(1 - Dr); residuo = (1 - Dr)*(1 - C)
    res = compute_depreciation(50, 100, ConservationState.MEDIOCRE)
    dr = 0.375
    c = 0.1810
    expected_total = dr + c * (1 - dr)
    assert res.total_depreciation == pytest.approx(round(expected_total, 4), abs=1e-3)
    assert res.residual_ratio == pytest.approx(round((1 - dr) * (1 - c), 4), abs=1e-3)


def test_age_beyond_life_caps():
    res = compute_depreciation(150, 100, ConservationState.GOOD)
    assert res.age_ratio == pytest.approx(1.0)
    assert res.ross_coefficient == pytest.approx(1.0)
    assert res.total_depreciation == pytest.approx(1.0)
    assert res.residual_ratio == pytest.approx(0.0)
    assert any("vita utile" in n for n in res.notes)


def test_negative_age_raises():
    with pytest.raises(ValueError):
        compute_depreciation(-1, 100, ConservationState.GOOD)


def test_zero_life_raises():
    with pytest.raises(ValueError):
        compute_depreciation(10, 0, ConservationState.GOOD)


def test_worse_state_increases_depreciation():
    good = compute_depreciation(30, 80, ConservationState.GOOD)
    poor = compute_depreciation(30, 80, ConservationState.POOR)
    assert poor.total_depreciation > good.total_depreciation
    assert poor.residual_ratio < good.residual_ratio
