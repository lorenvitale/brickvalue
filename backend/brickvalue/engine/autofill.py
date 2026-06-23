"""Arricchimento della richiesta con i parametri dedotti dall'indirizzo.

Collega geolocalizzazione e inferenza al motore: quando l'utente fornisce un
indirizzo e non specifica i parametri, questi vengono dedotti (valore di zona,
saggio, costo di costruzione regionale) prima del calcolo.
"""

from __future__ import annotations

from brickvalue.data.reference import construction_cost_for
from brickvalue.domain.geo import GeoLookupResult
from brickvalue.domain.inputs import CostInput, MarketInput, ValuationRequest
from brickvalue.domain.enums import PropertyType, ValuationPurpose
from brickvalue.domain.results import ValuationReport
from brickvalue.engine.inference import infer_parameters
from brickvalue.engine.quick import expand_quick
from brickvalue.engine.valuator import valuate
from brickvalue.geo.client import Fetcher, resolve_location
from brickvalue.utils import round_money


def lookup_address(
    address: str,
    property_type: PropertyType | None = None,
    *,
    api_key: str | None = None,
    fetch: Fetcher | None = None,
) -> GeoLookupResult:
    """Risolve l'indirizzo e deduce i parametri di stima."""
    location = resolve_location(address, api_key=api_key, fetch=fetch)
    parameters = infer_parameters(location, property_type)
    return GeoLookupResult(location=location, parameters=parameters)


def enrich_request(
    req: ValuationRequest,
    *,
    fetch: Fetcher | None = None,
) -> tuple[ValuationRequest, GeoLookupResult | None]:
    """Restituisce la richiesta arricchita e l'eventuale lookup geografico."""
    if not req.auto_parameters:
        return req, None
    location = req.property.location
    address = location.address if location else None
    if not address or not address.strip():
        return req, None

    lookup = lookup_address(address, req.property.property_type, fetch=fetch)
    params = lookup.parameters
    updates: dict = {}

    # Valore unitario di mercato dedotto (solo se non gia' fornito)
    if req.market is None and params.base_unit_value:
        updates["market"] = MarketInput(base_unit_value=params.base_unit_value)

    # Costo di costruzione regionale: solo dove il metodo del costo e' pertinente
    cost_relevant = req.cost is not None or req.purpose in (
        ValuationPurpose.INSURANCE,
        ValuationPurpose.TECHNICAL,
    )
    if (
        cost_relevant
        and not req.property.property_type.is_land
        and abs(params.construction_cost_multiplier - 1.0) > 1e-9
    ):
        cost = req.cost
        if cost is None or cost.construction_cost_per_sqm is None:
            base = construction_cost_for(req.property.property_type)
            ccs = round_money(base * params.construction_cost_multiplier)
            if cost is None:
                updates["cost"] = CostInput(construction_cost_per_sqm=ccs)
            else:
                updates["cost"] = cost.model_copy(update={"construction_cost_per_sqm": ccs})

    # Saggio di capitalizzazione dedotto (solo se reddito presente e saggio assente)
    if req.income is not None and req.income.cap_rate is None and params.cap_rate:
        updates["income"] = req.income.model_copy(update={"cap_rate": params.cap_rate})

    if updates:
        req = req.model_copy(update=updates)
    return req, lookup


def run_valuation(req: ValuationRequest, *, fetch: Fetcher | None = None) -> ValuationReport:
    """Arricchisce la richiesta dall'indirizzo, esegue la stima e allega il geo-lookup."""
    enriched, lookup = enrich_request(req, fetch=fetch)
    report = valuate(enriched)
    if lookup is not None:
        report.geo = lookup
        if lookup.location.source == "google":
            report.methodology_notes.append("Indirizzo geolocalizzato con Google Maps.")
        elif lookup.location.source == "fallback_testuale":
            report.methodology_notes.append(
                "Indirizzo riconosciuto dal dataset di riferimento (Google Maps non configurato)."
            )
    return report


def run_quick(q, *, fetch: Fetcher | None = None) -> ValuationReport:
    """Esegue la valutazione rapida con deduzione dei parametri dall'indirizzo."""
    return run_valuation(expand_quick(q), fetch=fetch)
