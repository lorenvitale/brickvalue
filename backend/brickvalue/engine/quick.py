"""Espansione della valutazione rapida (versione base) verso il motore completo.

Mappa i pochi campi della :class:`QuickValuationRequest` su una
:class:`ValuationRequest` completa, applicando default ragionevoli, e delega il
calcolo a :func:`brickvalue.engine.valuator.valuate`.
"""

from __future__ import annotations

from brickvalue.domain.enums import (
    ConservationState,
    PropertyType,
    ValuationPurpose,
)
from brickvalue.domain.inputs import MarketInput, ValuationRequest
from brickvalue.domain.property import Location, PropertyInput
from brickvalue.domain.quick import (
    BuildingScope,
    QuickGoal,
    QuickValuationRequest,
    SimpleCondition,
)
from brickvalue.domain.results import ValuationReport
from brickvalue.domain.surface import SurfaceComponent, SurfaceInput
from brickvalue.engine.valuator import valuate

_CONDITION: dict[SimpleCondition, ConservationState] = {
    SimpleCondition.AS_NEW: ConservationState.EXCELLENT,
    SimpleCondition.GOOD: ConservationState.GOOD,
    SimpleCondition.TO_FIX: ConservationState.TO_RENOVATE,
}

_PURPOSE: dict[QuickGoal, ValuationPurpose] = {
    QuickGoal.INSURANCE: ValuationPurpose.INSURANCE,
    QuickGoal.MARKET: ValuationPurpose.MARKET,
    QuickGoal.BANKING: ValuationPurpose.BANKING,
}


def expand_quick(q: QuickValuationRequest) -> ValuationRequest:
    """Converte la richiesta rapida in una richiesta completa."""
    is_building = q.scope == BuildingScope.BUILDING
    property_type = PropertyType.BUILDING if is_building else q.property_type

    location = Location(address=q.address) if q.address else None
    prop = PropertyInput(
        property_type=property_type,
        conservation=_CONDITION[q.condition],
        year_built=q.year_built,
        floor=q.floor if not is_building else None,
        total_floors=q.total_floors,
        location=location,
    )

    surface = SurfaceInput(
        components=[SurfaceComponent(type="superficie_principale", area=q.total_area)]
    )

    market = MarketInput(base_unit_value=q.base_unit_value) if q.base_unit_value else None

    return ValuationRequest(
        property=prop,
        surface=surface,
        purpose=_PURPOSE[q.goal],
        market=market,
    )


def quick_valuate(q: QuickValuationRequest) -> ValuationReport:
    """Esegue la valutazione rapida e restituisce il report completo."""
    return valuate(expand_quick(q))
