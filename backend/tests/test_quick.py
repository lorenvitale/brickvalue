"""Test della valutazione rapida (versione base)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from brickvalue.domain.enums import ConservationState, PropertyType, ValuationPurpose
from brickvalue.domain.quick import (
    BuildingScope,
    QuickGoal,
    QuickValuationRequest,
    SimpleCondition,
)
from brickvalue.engine.quick import expand_quick, quick_valuate


def test_insurance_single_unit():
    q = QuickValuationRequest(
        goal=QuickGoal.INSURANCE,
        scope=BuildingScope.UNIT,
        area_sqm=100.0,
        year_built=2000,
        condition=SimpleCondition.GOOD,
    )
    report = quick_valuate(q)
    assert report.purpose == ValuationPurpose.INSURANCE
    assert report.reconstruction_value_new is not None
    assert report.reconstruction_value_new > 0
    assert report.recommended_value == report.reconstruction_value_new


def test_insurance_needs_no_market_data():
    # L'assicurazione (ricostruzione) non richiede prezzo di zona
    q = QuickValuationRequest(goal=QuickGoal.INSURANCE, area_sqm=80.0)
    report = quick_valuate(q)
    assert report.reconstruction_value_new is not None


def test_market_single_unit():
    q = QuickValuationRequest(
        goal=QuickGoal.MARKET,
        area_sqm=100.0,
        condition=SimpleCondition.GOOD,
        base_unit_value=2000.0,
    )
    report = quick_valuate(q)
    # GOOD -> coefficiente conservazione 1.05 ; nessun altro merito
    assert report.market_value == pytest.approx(100.0 * 2000.0 * 1.05)
    assert report.recommended_value == report.market_value


def test_whole_building_area_aggregation():
    q = QuickValuationRequest(
        goal=QuickGoal.INSURANCE,
        scope=BuildingScope.BUILDING,
        num_units=10,
        avg_unit_sqm=85.0,
    )
    expanded = expand_quick(q)
    assert expanded.property.property_type == PropertyType.BUILDING
    assert expanded.surface.components[0].area == pytest.approx(850.0)
    report = quick_valuate(q)
    assert report.surface.commercial_surface == pytest.approx(850.0)
    assert report.reconstruction_value_new is not None


def test_condition_mapping():
    q = QuickValuationRequest(goal=QuickGoal.INSURANCE, area_sqm=90.0, condition=SimpleCondition.TO_FIX)
    expanded = expand_quick(q)
    assert expanded.property.conservation == ConservationState.TO_RENOVATE


def test_banking_goal_maps_purpose():
    q = QuickValuationRequest(goal=QuickGoal.BANKING, area_sqm=90.0, base_unit_value=2500.0)
    report = quick_valuate(q)
    assert report.purpose == ValuationPurpose.BANKING
    assert report.recommended_value == report.mortgage_lending_value


def test_address_passed_through():
    q = QuickValuationRequest(
        goal=QuickGoal.INSURANCE, area_sqm=90.0, address="Via Roma 1, Milano", floor=2
    )
    expanded = expand_quick(q)
    assert expanded.property.location is not None
    assert expanded.property.location.address == "Via Roma 1, Milano"
    assert expanded.property.floor == 2


def test_building_floor_ignored():
    # Per l'intero edificio il "piano" della singola unita' non si applica
    q = QuickValuationRequest(
        goal=QuickGoal.INSURANCE, scope=BuildingScope.BUILDING, num_units=4, floor=3
    )
    expanded = expand_quick(q)
    assert expanded.property.floor is None


def test_unit_requires_area():
    with pytest.raises(ValidationError):
        QuickValuationRequest(goal=QuickGoal.INSURANCE, scope=BuildingScope.UNIT)


def test_building_requires_units():
    with pytest.raises(ValidationError):
        QuickValuationRequest(goal=QuickGoal.INSURANCE, scope=BuildingScope.BUILDING)


def test_market_requires_base_unit_value():
    with pytest.raises(ValidationError):
        QuickValuationRequest(goal=QuickGoal.MARKET, area_sqm=90.0)
