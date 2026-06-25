"""Approccio del confronto di mercato (Market Comparison Approach).

Due modalita':

* **valore_unitario** — a partire dal valore unitario di zona (€/m², es. OMI)
  corretto da coefficienti di merito specifici del subject.
* **comparables** — media ponderata dei prezzi unitari di immobili comparabili,
  resi omogenei tramite aggiustamenti percentuali netti.
"""

from __future__ import annotations

from brickvalue.data.reference import CONSERVATION_MERIT, ENERGY_MERIT
from brickvalue.domain.inputs import MarketInput, ValuationRequest
from brickvalue.domain.property import PropertyInput
from brickvalue.domain.results import MarketResult, SurfaceResult
from brickvalue.utils import clamp, product, round_money


def floor_coefficient(prop: PropertyInput) -> float:
    """Coefficiente di merito legato al piano e alla presenza di ascensore."""
    # L'attico e' pregiato a prescindere dal piano esplicito.
    if prop.is_penthouse:
        return 1.08 if prop.has_elevator else 0.97
    if prop.floor is None:
        return 1.0
    floor = prop.floor

    if floor < 0:
        # Interrati / seminterrati
        return 0.80
    if floor == 0:
        # Piano terra: pregio per il commerciale (vetrina), penalita' per il residenziale
        return 1.05 if prop.property_type.is_commercial else 0.93
    # Piani fuori terra
    if prop.has_elevator:
        return 1.00
    # Senza ascensore: penalita' crescente con il piano
    return clamp(1.0 - 0.035 * (floor - 1), 0.78, 1.0)


def _merit(prop: PropertyInput, market: MarketInput, use_auto: bool) -> tuple[float, dict[str, float]]:
    """Calcola il moltiplicatore di merito e il relativo dettaglio.

    ``use_auto`` abilita i coefficienti automatici (conservazione, energetica,
    piano). Con i comparables vanno tipicamente esclusi per non duplicare gli
    aggiustamenti gia' applicati a ciascun comparabile.
    """
    factors: list[float] = []
    breakdown: dict[str, float] = {}

    if use_auto and market.apply_conservation_merit:
        cm = CONSERVATION_MERIT[prop.conservation]
        breakdown["conservazione"] = round(cm, 4)
        factors.append(cm)
    if use_auto and market.apply_energy_merit and prop.energy_class is not None:
        em = ENERGY_MERIT[prop.energy_class]
        breakdown["classe_energetica"] = round(em, 4)
        factors.append(em)
    if use_auto and market.apply_floor_merit:
        fm = floor_coefficient(prop)
        if abs(fm - 1.0) > 1e-9:
            breakdown["piano"] = round(fm, 4)
            factors.append(fm)
    for i, c in enumerate(market.extra_coefficients, start=1):
        breakdown[f"extra_{i}"] = round(c, 4)
        factors.append(c)

    return product(factors), breakdown


def compute_market(req: ValuationRequest, surface: SurfaceResult) -> MarketResult:
    """Calcola il valore con l'approccio del confronto di mercato."""
    if req.market is None:  # pragma: no cover - difensivo, garantito dall'orchestratore
        raise ValueError("Parametri di mercato assenti")

    market = req.market
    cs = surface.commercial_surface
    notes: list[str] = []
    comparables_detail: list[dict] = []

    if market.comparables:
        approach = "comparables"
        total_weight = sum(c.weight for c in market.comparables)
        base_unit = sum(c.adjusted_unit_price * c.weight for c in market.comparables) / total_weight
        for c in market.comparables:
            comparables_detail.append(
                {
                    "label": c.label,
                    "price": round_money(c.price),
                    "commercial_surface": round(c.commercial_surface, 2),
                    "unit_price": round_money(c.unit_price),
                    "net_adjustment": round(c.net_adjustment, 4),
                    "adjusted_unit_price": round_money(c.adjusted_unit_price),
                    "weight": c.weight,
                }
            )
        if market.base_unit_value is not None:
            notes.append("Forniti sia comparabili sia valore unitario: usati i comparabili.")
        # Con i comparables i coefficienti automatici sono esclusi (gia' nei singoli
        # aggiustamenti); restano applicabili gli eventuali extra_coefficients.
        merit, breakdown = _merit(req.property, market, use_auto=False)
        if market.extra_coefficients:
            notes.append("Applicati coefficienti di merito extra ai prezzi dei comparabili.")
        notes.append(f"Stima su {len(market.comparables)} comparabili (media ponderata).")
    else:
        approach = "valore_unitario"
        base_unit = float(market.base_unit_value)  # garantito non-None dal validatore
        merit, breakdown = _merit(req.property, market, use_auto=True)

    adjusted_unit = base_unit * merit
    value = adjusted_unit * cs

    return MarketResult(
        approach=approach,
        commercial_surface=round(cs, 2),
        base_unit_value=round_money(base_unit),
        merit_multiplier=round(merit, 4),
        merit_breakdown=breakdown,
        adjusted_unit_value=round_money(adjusted_unit),
        value=round_money(value),
        comparables_detail=comparables_detail,
        notes=notes,
    )
