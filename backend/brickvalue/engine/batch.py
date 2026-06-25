"""Motore della stima massiva: valuta in blocco un elenco di immobili.

Per ogni riga costruisce una richiesta completa (superficie principale = mq,
indirizzo per la deduzione dei parametri) ed esegue la valutazione tramite la
pipeline con autofill. Gli errori sono isolati per riga.
"""

from __future__ import annotations

from brickvalue.domain.batch import (
    BatchItem,
    BatchItemResult,
    BatchResult,
    BatchValuationRequest,
)
from brickvalue.domain.inputs import MarketInput, ValuationRequest
from brickvalue.domain.property import Location, PropertyInput
from brickvalue.domain.surface import SurfaceComponent, SurfaceInput
from brickvalue.engine.autofill import run_valuation
from brickvalue.geo.client import Fetcher


def _valuate_item(item: BatchItem, fetch: Fetcher | None) -> BatchItemResult:
    location = Location(address=item.address) if item.address else None
    request = ValuationRequest(
        property=PropertyInput(
            property_type=item.property_type,
            conservation=item.condition,
            year_built=item.year_built,
            location=location,
        ),
        surface=SurfaceInput(
            components=[SurfaceComponent(type="superficie_principale", area=item.area_sqm)]
        ),
        purpose=item.purpose,
        market=MarketInput(base_unit_value=item.base_unit_value) if item.base_unit_value else None,
    )
    report = run_valuation(request, fetch=fetch)
    geo = report.geo
    return BatchItemResult(
        label=item.label,
        address=item.address,
        city=(geo.parameters.city if geo else None),
        region=(geo.parameters.region if geo else None),
        purpose=item.purpose,
        commercial_surface=report.surface.commercial_surface,
        unit_value=report.unit_market_value,
        market_value=report.market_value,
        reconstruction_value_new=report.reconstruction_value_new,
        recommended_value=report.recommended_value,
        recommended_label=report.recommended_value_label,
        confidence=(geo.parameters.confidence if geo else None),
    )


def compute_batch(req: BatchValuationRequest, *, fetch: Fetcher | None = None) -> BatchResult:
    """Valuta tutte le righe, isolando gli errori per riga."""
    results: list[BatchItemResult] = []
    total_market = 0.0
    total_recon = 0.0
    ok = 0

    for item in req.items:
        try:
            res = _valuate_item(item, fetch)
            ok += 1
            total_market += res.market_value or 0.0
            total_recon += res.reconstruction_value_new or 0.0
        except Exception as exc:  # noqa: BLE001 - isolamento per riga
            res = BatchItemResult(
                label=item.label, address=item.address, purpose=item.purpose, error=str(exc)
            )
        results.append(res)

    return BatchResult(
        count=len(req.items),
        ok=ok,
        errors=len(req.items) - ok,
        total_market_value=round(total_market, 2),
        total_reconstruction_value=round(total_recon, 2),
        items=results,
    )
