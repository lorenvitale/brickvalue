"""Fixtures condivise per i test."""

from __future__ import annotations

import os

import pytest

# I test non devono dipendere dalla rete: disattiva i provider online (Photon).
# I percorsi che iniettano un ``fetch`` restano testabili.
os.environ.setdefault("BRICKVALUE_OFFLINE", "1")

from brickvalue.domain.enums import (
    ConservationState,
    EnergyClass,
    PropertyType,
    StructureType,
)
from brickvalue.domain.inputs import (
    CostInput,
    IncomeInput,
    MarketInput,
    ValuationRequest,
)
from brickvalue.domain.property import PropertyInput
from brickvalue.domain.surface import SurfaceComponent, SurfaceInput


@pytest.fixture
def simple_surface() -> SurfaceInput:
    return SurfaceInput(
        components=[
            SurfaceComponent(type="superficie_principale", area=100.0),
            SurfaceComponent(type="balcone_scoperto", area=10.0),
        ]
    )


@pytest.fixture
def apartment() -> PropertyInput:
    return PropertyInput(
        property_type=PropertyType.APARTMENT,
        structure=StructureType.REINFORCED_CONCRETE,
        conservation=ConservationState.GOOD,
        energy_class=EnergyClass.C,
        year_built=2000,
        floor=2,
        total_floors=4,
        has_elevator=True,
    )


@pytest.fixture
def full_request(apartment: PropertyInput, simple_surface: SurfaceInput) -> ValuationRequest:
    return ValuationRequest(
        property=apartment,
        surface=simple_surface,
        market=MarketInput(base_unit_value=3000.0),
        cost=CostInput(land_value=50000.0),
        income=IncomeInput(monthly_rent=1000.0),
        reference_year=2025,
    )
