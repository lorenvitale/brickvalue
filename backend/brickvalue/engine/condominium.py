"""Motore di valutazione del condominio (valore di ricostruzione a nuovo).

Calcola il costo di ricostruzione dell'intero fabbricato (parti private + parti
comuni) comprensivo di spese tecniche, spese generali e utile, demolizione e
sgombero macerie ed eventuale IVA; quindi ripartisce la somma da assicurare per
unita' (per millesimi, in subordine per superficie, infine per quote uguali).
"""

from __future__ import annotations

from brickvalue.data.market_reference import construction_multiplier, resolve_region
from brickvalue.data.reference import construction_cost_for
from brickvalue.domain.condominium import (
    CondominiumReport,
    CondominiumRequest,
    CondoUnitResult,
)
from brickvalue.domain.enums import PropertyType
from brickvalue.domain.geo import GeoLookupResult
from brickvalue.engine.inference import infer_parameters
from brickvalue.geo.client import Fetcher, resolve_location
from brickvalue.utils import round_money, safe_div


def _resolve_region_multiplier(
    req: CondominiumRequest, fetch: Fetcher | None
) -> tuple[str | None, float, GeoLookupResult | None]:
    """Regione e moltiplicatore del costo di costruzione dall'indirizzo (se presente)."""
    if not (req.auto_parameters and req.address and req.address.strip()):
        return None, 1.0, None
    location = resolve_location(req.address, fetch=fetch)
    parameters = infer_parameters(location, PropertyType.BUILDING)
    region = parameters.region or resolve_region(location.region)
    return region, parameters.construction_cost_multiplier, GeoLookupResult(
        location=location, parameters=parameters
    )


def compute_condominium(req: CondominiumRequest, *, fetch: Fetcher | None = None) -> CondominiumReport:
    """Calcola il valore di ricostruzione a nuovo del condominio e la ripartizione."""
    notes: list[str] = []
    warnings: list[str] = []

    region, mult, geo = _resolve_region_multiplier(req, fetch)

    # Costo di costruzione unitario
    if req.construction_cost_per_sqm is not None:
        cost_psqm = req.construction_cost_per_sqm
        mult = 1.0
    else:
        cost_psqm = round_money(construction_cost_for(PropertyType.BUILDING) * mult)
        notes.append("Costo di costruzione da dati di riferimento per fabbricati.")
        if abs(mult - 1.0) > 1e-9:
            notes.append(f"Moltiplicatore regionale del costo ({region}): ×{mult:.2f}.")

    residential = req.residential_area
    gross = residential + req.common_area_sqm
    if gross <= 0:
        raise ValueError("Superficie complessiva nulla: verificare i dati")

    bare = gross * cost_psqm
    technical = bare * req.technical_fees_pct
    overhead = bare * req.overhead_profit_pct
    demolition = bare * req.demolition_pct
    subtotal = bare + technical + overhead + demolition
    vat = subtotal * req.vat_pct
    total = subtotal + vat
    value_per_sqm = safe_div(total, gross)

    # Ripartizione
    units_out: list[CondoUnitResult] = []
    if req.units:
        have_millesimi = all(u.millesimi for u in req.units)
        if have_millesimi:
            basis = "millesimi"
            weights = [u.millesimi for u in req.units]
        else:
            basis = "superficie"
            weights = [u.surface_sqm for u in req.units]
            if any(u.millesimi for u in req.units):
                warnings.append("Millesimi incompleti: ripartizione per superficie.")
        total_w = sum(weights)
        for unit, w in zip(req.units, weights):
            quota = safe_div(w, total_w)
            units_out.append(
                CondoUnitResult(
                    label=unit.label or "Unita'",
                    surface_sqm=unit.surface_sqm,
                    millesimi=unit.millesimi,
                    quota_pct=round(quota, 6),
                    insured_value=round_money(total * quota),
                )
            )
    else:
        basis = "quote_uguali"
        n = req.unit_count
        quota = safe_div(1.0, n)
        notes.append("Ripartizione per quote uguali (dati per unita' non forniti).")
        for i in range(n):
            units_out.append(
                CondoUnitResult(
                    label=f"Unita' {i + 1}",
                    quota_pct=round(quota, 6),
                    insured_value=round_money(total * quota),
                )
            )

    return CondominiumReport(
        geo=geo,
        region=region,
        construction_cost_per_sqm=round_money(cost_psqm),
        regional_multiplier=round(mult, 4),
        residential_area=round(residential, 2),
        common_area=round(req.common_area_sqm, 2),
        gross_area=round(gross, 2),
        unit_count=req.unit_count,
        bare_construction_cost=round_money(bare),
        technical_fees=round_money(technical),
        overhead_profit=round_money(overhead),
        demolition_cost=round_money(demolition),
        vat=round_money(vat),
        reconstruction_value_new=round_money(total),
        value_per_sqm=round_money(value_per_sqm),
        allocation_basis=basis,
        units=units_out,
        warnings=warnings,
        notes=notes,
    )
