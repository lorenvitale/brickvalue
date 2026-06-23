"""Test dell'orchestratore di valutazione end-to-end."""

from __future__ import annotations

import pytest

from brickvalue.domain.enums import (
    PropertyType,
    ValuationMethod,
    ValuationPurpose,
)
from brickvalue.domain.inputs import (
    CostInput,
    IncomeInput,
    MarketInput,
    ValuationRequest,
)
from brickvalue.domain.property import PropertyInput
from brickvalue.domain.surface import SurfaceComponent, SurfaceInput
from brickvalue.engine.valuator import valuate


def test_full_valuation(full_request):
    report = valuate(full_request)
    assert report.market is not None
    assert report.cost is not None
    assert report.income is not None
    assert report.market_value > 0
    assert report.unit_market_value > 0
    assert report.reconstruction_value_new is not None


def test_value_ordering(full_request):
    report = valuate(full_request)
    # pronto realizzo < cauzionale < valore di mercato (con haircut di default)
    assert report.forced_sale_value < report.mortgage_lending_value < report.market_value
    assert report.value_range.min < report.value_range.most_likely < report.value_range.max


def test_insurance_recommends_reconstruction(apartment, simple_surface):
    req = ValuationRequest(
        property=apartment,
        surface=simple_surface,
        purpose=ValuationPurpose.INSURANCE,
        market=MarketInput(base_unit_value=3000.0),
    )
    report = valuate(req)
    assert report.cost is not None
    assert report.recommended_value == report.reconstruction_value_new
    assert "ricostruzione" in report.recommended_value_label.lower()


def test_banking_recommends_mortgage_value(full_request):
    full_request.purpose = ValuationPurpose.BANKING
    report = valuate(full_request)
    assert report.recommended_value == report.mortgage_lending_value
    assert "cauzionale" in report.recommended_value_label.lower()


def test_technical_recommends_cost_value(full_request):
    full_request.purpose = ValuationPurpose.TECHNICAL
    report = valuate(full_request)
    assert report.cost is not None
    assert report.recommended_value == report.cost.market_value_via_cost


def test_land_skips_cost_method():
    surface = SurfaceInput(components=[SurfaceComponent(type="superficie_principale", area=800.0)])
    prop = PropertyInput(property_type=PropertyType.BUILDABLE_LAND)
    req = ValuationRequest(
        property=prop,
        surface=surface,
        market=MarketInput(base_unit_value=150.0),
    )
    report = valuate(req)
    assert report.cost is None
    assert report.reconstruction_value_new is None
    # 800 m² * 150 €/m² = 120000
    assert report.market_value == pytest.approx(120000.0)


def test_cost_only_fallback_when_no_inputs(apartment, simple_surface):
    # Solo immobile e superficie: il sistema ripiega sul metodo del costo
    req = ValuationRequest(property=apartment, surface=simple_surface)
    report = valuate(req)
    assert report.cost is not None
    assert report.market is None
    assert report.income is None
    assert any("solo metodo del costo" in w for w in report.warnings)
    assert report.market_value > 0


def test_explicit_methods_selection(full_request):
    full_request.methods = [ValuationMethod.MARKET_COMPARISON]
    report = valuate(full_request)
    assert report.market is not None
    assert report.cost is None
    assert report.income is None


def test_requested_method_without_input_is_skipped(apartment, simple_surface):
    req = ValuationRequest(
        property=apartment,
        surface=simple_surface,
        market=MarketInput(base_unit_value=3000.0),
        methods=[ValuationMethod.MARKET_COMPARISON, ValuationMethod.INCOME],
    )
    report = valuate(req)
    assert report.market is not None
    assert report.income is None
    assert any("reddituale" in w.lower() for w in report.warnings)


def test_reference_year_affects_depreciation(apartment, simple_surface):
    apartment.year_built = 1980
    req_old = ValuationRequest(
        property=apartment, surface=simple_surface,
        cost=CostInput(land_value=0.0), reference_year=2025,
    )
    report = valuate(req_old)
    assert report.cost is not None
    assert report.cost.depreciation is not None
    assert report.cost.depreciation.age_years == 45


def test_unit_value_consistency(full_request):
    report = valuate(full_request)
    expected_unit = report.market_value / report.surface.commercial_surface
    assert report.unit_market_value == pytest.approx(expected_unit, rel=1e-3)
