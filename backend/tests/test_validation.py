"""Test della validazione degli input (robustezza/anti-bug)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from brickvalue.domain.enums import PropertyType
from brickvalue.domain.property import PropertyInput


def test_renovation_before_construction_rejected():
    with pytest.raises(ValidationError):
        PropertyInput(property_type=PropertyType.APARTMENT, year_built=2000, year_renovated=1990)


def test_floor_above_total_floors_rejected():
    with pytest.raises(ValidationError):
        PropertyInput(property_type=PropertyType.APARTMENT, floor=6, total_floors=4)


def test_age_uses_renovation_year():
    prop = PropertyInput(
        property_type=PropertyType.APARTMENT, year_built=1980, year_renovated=2010
    )
    assert prop.age(2025) == 15


def test_age_none_without_year():
    prop = PropertyInput(property_type=PropertyType.APARTMENT)
    assert prop.age(2025) is None


def test_age_never_negative():
    prop = PropertyInput(property_type=PropertyType.APARTMENT, year_built=2030)
    assert prop.age(2025) == 0


def test_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        PropertyInput(property_type=PropertyType.APARTMENT, unknown_field=1)


def test_property_type_helpers():
    assert PropertyType.APARTMENT.is_residential
    assert PropertyType.SHOP.is_commercial
    assert PropertyType.BUILDABLE_LAND.is_land
    assert not PropertyType.APARTMENT.is_land
