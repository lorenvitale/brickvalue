"""Approccio del costo / valore di ricostruzione a nuovo.

Calcola:

* il **valore di ricostruzione a nuovo** (finalita' assicurativa), comprensivo di
  spese tecniche, spese generali e utile, oneri, eventuali costi di demolizione e
  IVA, ma *senza* suolo e *senza* deprezzamento;
* il **valore di mercato da costo**, ottenuto deprezzando il costo di costruzione
  (Ross-Heidecke) e sommando il valore del suolo.
"""

from __future__ import annotations

from brickvalue.data.reference import construction_cost_for, useful_life_for
from brickvalue.domain.inputs import CostInput, ValuationRequest
from brickvalue.domain.results import CostResult, SurfaceResult
from brickvalue.engine.depreciation import compute_depreciation
from brickvalue.utils import round_money


def compute_cost(req: ValuationRequest, surface: SurfaceResult) -> CostResult:
    """Calcola il valore con l'approccio del costo."""
    prop = req.property
    if prop.property_type.is_land:
        raise ValueError("L'approccio del costo non si applica ai terreni")

    cost = req.cost if req.cost is not None else CostInput()
    notes: list[str] = []

    # Superficie lorda
    if cost.gross_floor_area is not None:
        gfa = cost.gross_floor_area
    elif surface.main_area > 0:
        gfa = surface.main_area
        notes.append("Superficie lorda derivata dalla superficie principale.")
    else:
        gfa = surface.commercial_surface
        notes.append("Superficie lorda derivata dalla superficie commerciale.")

    # Costo di costruzione unitario
    if cost.construction_cost_per_sqm is not None:
        ccs = cost.construction_cost_per_sqm
    else:
        ccs = construction_cost_for(prop.property_type)
        notes.append("Costo di costruzione unitario da dati di riferimento.")

    bare = gfa * ccs
    technical = bare * cost.technical_fees_pct
    overhead = bare * cost.overhead_profit_pct
    urban = cost.urbanization_charges
    demolition = cost.demolition_cost
    subtotal = bare + technical + overhead + urban + demolition
    vat = subtotal * cost.vat_pct
    reconstruction_new = subtotal + vat

    # Deprezzamento (Ross-Heidecke)
    age = prop.age(req.reference_year)
    depreciation = None
    if age is not None:
        useful = cost.useful_life_years or useful_life_for(prop.structure)
        depreciation = compute_depreciation(age, useful, prop.conservation)
        depreciated = reconstruction_new * depreciation.residual_ratio
    else:
        depreciated = reconstruction_new
        notes.append(
            "Anno di costruzione non noto: valore di mercato da costo senza deprezzamento."
        )

    land = cost.land_value if cost.land_value is not None else 0.0
    if cost.land_value is None:
        notes.append("Valore del suolo non fornito: escluso dal valore di mercato da costo.")
    market_via_cost = depreciated + land

    return CostResult(
        gross_floor_area=round(gfa, 2),
        construction_cost_per_sqm=round_money(ccs),
        bare_construction_cost=round_money(bare),
        technical_fees=round_money(technical),
        overhead_profit=round_money(overhead),
        urbanization_charges=round_money(urban),
        vat=round_money(vat),
        demolition_cost=round_money(demolition),
        reconstruction_cost_new=round_money(reconstruction_new),
        depreciation=depreciation,
        depreciated_construction_value=round_money(depreciated),
        land_value=round_money(land),
        market_value_via_cost=round_money(market_via_cost),
        notes=notes,
    )
