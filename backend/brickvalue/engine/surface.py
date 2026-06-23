"""Calcolo della superficie commerciale (ragguaglio delle superfici)."""

from __future__ import annotations

from brickvalue.data.reference import surface_coefficient
from brickvalue.domain.enums import SurfaceComponentType
from brickvalue.domain.results import SurfaceLine, SurfaceResult
from brickvalue.domain.surface import SurfaceInput
from brickvalue.utils import round_area


def compute_surface(surface: SurfaceInput) -> SurfaceResult:
    """Calcola la superficie commerciale ragguagliata.

    Per ogni componente applica il coefficiente di ragguaglio (quello indicato
    in input oppure il default di riferimento) e somma le superfici pesate.
    L'eventuale incidenza dei muri viene aggiunta alla superficie principale.
    """
    lines: list[SurfaceLine] = []
    commercial = 0.0
    main_area = 0.0

    for component in surface.components:
        coef = (
            component.coefficient
            if component.coefficient is not None
            else surface_coefficient(component.type)
        )
        weighted = component.area * coef
        commercial += weighted
        if component.type == SurfaceComponentType.MAIN:
            main_area += component.area
        lines.append(
            SurfaceLine(
                type=component.type,
                label=component.label,
                area=round_area(component.area),
                coefficient=round(coef, 4),
                weighted_area=round_area(weighted),
            )
        )

    wall_added = main_area * surface.wall_incidence_pct
    commercial += wall_added

    return SurfaceResult(
        lines=lines,
        main_area=round_area(main_area),
        wall_incidence_pct=surface.wall_incidence_pct,
        wall_area_added=round_area(wall_added),
        commercial_surface=round_area(commercial),
    )
