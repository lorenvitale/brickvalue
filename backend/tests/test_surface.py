"""Test del calcolo della superficie commerciale."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from brickvalue.domain.surface import SurfaceComponent, SurfaceInput
from brickvalue.engine.surface import compute_surface


def test_basic_weighting():
    surf = SurfaceInput(
        components=[
            SurfaceComponent(type="superficie_principale", area=100.0),
            SurfaceComponent(type="balcone_scoperto", area=10.0),  # coef 0.30
            SurfaceComponent(type="cantina_soffitta", area=8.0),  # coef 0.25
        ]
    )
    result = compute_surface(surf)
    assert result.main_area == 100.0
    # 100 + 10*0.30 + 8*0.25 = 100 + 3 + 2 = 105
    assert result.commercial_surface == pytest.approx(105.0)
    assert len(result.lines) == 3


def test_custom_coefficient_override():
    surf = SurfaceInput(
        components=[
            SurfaceComponent(type="superficie_principale", area=100.0),
            SurfaceComponent(type="terrazzo", area=20.0, coefficient=0.5),
        ]
    )
    result = compute_surface(surf)
    # 100 + 20*0.5 = 110
    assert result.commercial_surface == pytest.approx(110.0)
    assert result.lines[1].coefficient == 0.5


def test_wall_incidence_added_to_main():
    surf = SurfaceInput(
        components=[SurfaceComponent(type="superficie_principale", area=100.0)],
        wall_incidence_pct=0.10,
    )
    result = compute_surface(surf)
    # 100 + 100*0.10 = 110
    assert result.wall_area_added == pytest.approx(10.0)
    assert result.commercial_surface == pytest.approx(110.0)


def test_multiple_main_components_sum():
    surf = SurfaceInput(
        components=[
            SurfaceComponent(type="superficie_principale", area=60.0),
            SurfaceComponent(type="superficie_principale", area=40.0),
        ]
    )
    result = compute_surface(surf)
    assert result.main_area == 100.0
    assert result.commercial_surface == pytest.approx(100.0)


def test_empty_components_rejected():
    with pytest.raises(ValidationError):
        SurfaceInput(components=[])


def test_negative_area_rejected():
    with pytest.raises(ValidationError):
        SurfaceComponent(type="superficie_principale", area=-5.0)


def test_coefficient_out_of_range_rejected():
    with pytest.raises(ValidationError):
        SurfaceComponent(type="terrazzo", area=10.0, coefficient=5.0)
