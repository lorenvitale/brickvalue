"""Test dell'approccio del confronto di mercato."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from brickvalue.domain.enums import ConservationState, PropertyType
from brickvalue.domain.inputs import Comparable, MarketInput, ValuationRequest
from brickvalue.domain.property import PropertyInput
from brickvalue.domain.surface import SurfaceComponent, SurfaceInput
from brickvalue.engine.market import compute_market, floor_coefficient
from brickvalue.engine.surface import compute_surface


def _request(market: MarketInput, **prop_kwargs) -> tuple[ValuationRequest, object]:
    prop = PropertyInput(property_type=PropertyType.APARTMENT, **prop_kwargs)
    surface = SurfaceInput(components=[SurfaceComponent(type="superficie_principale", area=100.0)])
    req = ValuationRequest(property=prop, surface=surface, market=market)
    return req, compute_surface(surface)


def test_unit_value_with_conservation_merit():
    req, surf = _request(
        MarketInput(base_unit_value=2000.0), conservation=ConservationState.NORMAL
    )
    res = compute_market(req, surf)
    # merit conservazione normale = 1.0 -> 2000 * 100 = 200000
    assert res.approach == "valore_unitario"
    assert res.adjusted_unit_value == pytest.approx(2000.0)
    assert res.value == pytest.approx(200000.0)


def test_conservation_merit_applied():
    req, surf = _request(
        MarketInput(base_unit_value=2000.0), conservation=ConservationState.EXCELLENT
    )
    res = compute_market(req, surf)
    # ottimo = 1.10
    assert res.merit_breakdown["conservazione"] == pytest.approx(1.10)
    assert res.adjusted_unit_value == pytest.approx(2200.0)


def test_comparables_weighted_mean():
    market = MarketInput(
        comparables=[
            Comparable(price=200000, commercial_surface=100, net_adjustment=0.0, weight=1),
            Comparable(price=220000, commercial_surface=100, net_adjustment=0.0, weight=1),
        ]
    )
    req, surf = _request(market)
    res = compute_market(req, surf)
    # media unit price (2000 + 2200)/2 = 2100 -> *100 = 210000
    assert res.approach == "comparables"
    assert res.base_unit_value == pytest.approx(2100.0)
    assert res.value == pytest.approx(210000.0)
    assert len(res.comparables_detail) == 2


def test_comparable_net_adjustment():
    market = MarketInput(
        comparables=[
            Comparable(price=200000, commercial_surface=100, net_adjustment=0.10, weight=1),
        ]
    )
    req, surf = _request(market)
    res = compute_market(req, surf)
    # unit price 2000 * 1.10 = 2200 -> *100 = 220000
    assert res.value == pytest.approx(220000.0)


def test_comparables_exclude_auto_merit():
    # Con i comparables i coefficienti automatici NON vanno applicati
    market = MarketInput(
        comparables=[Comparable(price=200000, commercial_surface=100, weight=1)],
    )
    req, surf = _request(market, conservation=ConservationState.EXCELLENT)
    res = compute_market(req, surf)
    assert res.merit_multiplier == pytest.approx(1.0)
    assert res.value == pytest.approx(200000.0)


def test_weighted_comparables_unequal_weights():
    market = MarketInput(
        comparables=[
            Comparable(price=200000, commercial_surface=100, weight=3),  # 2000
            Comparable(price=300000, commercial_surface=100, weight=1),  # 3000
        ]
    )
    req, surf = _request(market)
    res = compute_market(req, surf)
    # (2000*3 + 3000*1)/4 = 2250
    assert res.base_unit_value == pytest.approx(2250.0)


def test_market_requires_source():
    with pytest.raises(ValidationError):
        MarketInput()


def test_both_sources_uses_comparables_with_note():
    market = MarketInput(
        base_unit_value=9999.0,
        comparables=[Comparable(price=200000, commercial_surface=100, weight=1)],
    )
    req, surf = _request(market)
    res = compute_market(req, surf)
    assert res.approach == "comparables"
    assert res.value == pytest.approx(200000.0)  # base_unit_value ignorato
    assert any("comparabili" in n for n in res.notes)


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({"floor": 0}, 0.93),  # piano terra residenziale
        ({"floor": -1}, 0.80),  # interrato
        ({"floor": 2, "has_elevator": True}, 1.00),
        ({"is_penthouse": True, "has_elevator": True}, 1.08),
        ({"is_penthouse": True, "has_elevator": False}, 0.97),
    ],
)
def test_floor_coefficient(kwargs, expected):
    prop = PropertyInput(property_type=PropertyType.APARTMENT, **kwargs)
    assert floor_coefficient(prop) == pytest.approx(expected)


def test_floor_coefficient_no_elevator_penalty():
    prop = PropertyInput(property_type=PropertyType.APARTMENT, floor=4, has_elevator=False)
    # 1 - 0.035*3 = 0.895
    assert floor_coefficient(prop) == pytest.approx(0.895)


def test_floor_coefficient_unknown_is_neutral():
    prop = PropertyInput(property_type=PropertyType.APARTMENT)
    assert floor_coefficient(prop) == 1.0


def test_shop_ground_floor_premium():
    prop = PropertyInput(property_type=PropertyType.SHOP, floor=0)
    assert floor_coefficient(prop) == pytest.approx(1.05)
