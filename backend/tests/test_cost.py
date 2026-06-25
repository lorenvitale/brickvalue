"""Test dell'approccio del costo / ricostruzione."""

from __future__ import annotations

import pytest

from brickvalue.domain.enums import ConservationState, PropertyType, StructureType
from brickvalue.domain.inputs import CostInput, ValuationRequest
from brickvalue.domain.property import PropertyInput
from brickvalue.domain.surface import SurfaceComponent, SurfaceInput
from brickvalue.engine.cost import compute_cost
from brickvalue.engine.surface import compute_surface


def _request(cost: CostInput, **prop_kwargs) -> tuple[ValuationRequest, object]:
    defaults = dict(property_type=PropertyType.APARTMENT, structure=StructureType.REINFORCED_CONCRETE)
    defaults.update(prop_kwargs)
    prop = PropertyInput(**defaults)
    surface = SurfaceInput(components=[SurfaceComponent(type="superficie_principale", area=100.0)])
    req = ValuationRequest(property=prop, surface=surface, cost=cost, reference_year=2025)
    return req, compute_surface(surface)


def test_reconstruction_new_components():
    cost = CostInput(
        gross_floor_area=100.0,
        construction_cost_per_sqm=1000.0,
        technical_fees_pct=0.10,
        overhead_profit_pct=0.20,
    )
    req, surf = _request(cost)
    res = compute_cost(req, surf)
    assert res.bare_construction_cost == pytest.approx(100000.0)
    assert res.technical_fees == pytest.approx(10000.0)
    assert res.overhead_profit == pytest.approx(20000.0)
    # 100000 + 10000 + 20000 = 130000 (no IVA, no oneri)
    assert res.reconstruction_cost_new == pytest.approx(130000.0)


def test_vat_applied_on_subtotal():
    cost = CostInput(
        gross_floor_area=100.0,
        construction_cost_per_sqm=1000.0,
        technical_fees_pct=0.0,
        overhead_profit_pct=0.0,
        vat_pct=0.10,
    )
    req, surf = _request(cost)
    res = compute_cost(req, surf)
    # 100000 * 1.10 = 110000
    assert res.vat == pytest.approx(10000.0)
    assert res.reconstruction_cost_new == pytest.approx(110000.0)


def test_depreciation_reduces_market_value():
    cost = CostInput(gross_floor_area=100.0, construction_cost_per_sqm=1000.0,
                     technical_fees_pct=0.0, overhead_profit_pct=0.0)
    req, surf = _request(cost, year_built=1985, conservation=ConservationState.NORMAL)
    res = compute_cost(req, surf)
    assert res.depreciation is not None
    # deprezzato < nuovo
    assert res.depreciated_construction_value < res.reconstruction_cost_new
    assert res.depreciated_construction_value == pytest.approx(
        res.reconstruction_cost_new * res.depreciation.residual_ratio, rel=1e-3
    )


def test_land_value_included():
    cost = CostInput(gross_floor_area=100.0, construction_cost_per_sqm=1000.0,
                     technical_fees_pct=0.0, overhead_profit_pct=0.0, land_value=40000.0)
    req, surf = _request(cost, year_built=2025)  # nuovo: nessun deprezzamento
    res = compute_cost(req, surf)
    assert res.land_value == 40000.0
    # nuovo (eta'=0) deprezzamento ~0 -> market_via_cost ~ reconstruction + land
    assert res.market_value_via_cost == pytest.approx(
        res.depreciated_construction_value + 40000.0
    )


def test_no_land_excluded_with_note():
    cost = CostInput(gross_floor_area=100.0, construction_cost_per_sqm=1000.0)
    req, surf = _request(cost, year_built=2010)
    res = compute_cost(req, surf)
    assert res.land_value == 0.0
    assert res.market_value_via_cost == pytest.approx(res.depreciated_construction_value)
    assert any("suolo" in n for n in res.notes)


def test_no_year_built_no_depreciation():
    cost = CostInput(gross_floor_area=100.0, construction_cost_per_sqm=1000.0)
    req, surf = _request(cost)  # year_built non fornito
    res = compute_cost(req, surf)
    assert res.depreciation is None
    assert res.depreciated_construction_value == pytest.approx(res.reconstruction_cost_new)


def test_reference_cost_used_when_absent():
    cost = CostInput(gross_floor_area=100.0)
    req, surf = _request(cost)
    res = compute_cost(req, surf)
    # appartamento -> 1350 €/m² di riferimento
    assert res.construction_cost_per_sqm == pytest.approx(1350.0)
    assert any("riferimento" in n for n in res.notes)


def test_gross_area_derived_from_main():
    cost = CostInput(construction_cost_per_sqm=1000.0)
    req, surf = _request(cost)
    res = compute_cost(req, surf)
    assert res.gross_floor_area == pytest.approx(100.0)
    assert any("superficie principale" in n.lower() for n in res.notes)


def test_land_property_not_supported():
    surface = SurfaceInput(components=[SurfaceComponent(type="superficie_principale", area=500.0)])
    prop = PropertyInput(property_type=PropertyType.BUILDABLE_LAND)
    req = ValuationRequest(property=prop, surface=surface, cost=CostInput())
    with pytest.raises(ValueError):
        compute_cost(req, compute_surface(surface))
