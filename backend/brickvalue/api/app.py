"""Applicazione FastAPI che espone il motore di valutazione."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, Field

from brickvalue import __version__
from brickvalue.data import reference
from brickvalue.domain.enums import PropertyType
from brickvalue.domain.batch import BatchResult, BatchValuationRequest
from brickvalue.domain.condominium import CondominiumReport, CondominiumRequest
from brickvalue.domain.geo import GeoLookupResult, SuggestResult
from brickvalue.domain.inputs import ValuationRequest
from brickvalue.domain.quick import QuickValuationRequest
from brickvalue.domain.results import SurfaceResult, ValuationReport
from brickvalue.domain.surface import SurfaceInput
from brickvalue.engine.autofill import lookup_address, run_quick, run_valuation
from brickvalue.engine.batch import compute_batch
from brickvalue.engine.condominium import compute_condominium
from brickvalue.engine.surface import compute_surface
from brickvalue.geo.client import is_google_enabled, suggest_addresses

_FRONTEND_DIR = Path(__file__).resolve().parents[3] / "frontend"


class GeocodeRequest(BaseModel):
    """Corpo della richiesta di geocodifica."""

    address: str = Field(min_length=1, max_length=300, description="Indirizzo da risolvere")
    property_type: PropertyType | None = Field(
        default=None, description="Tipologia (per affinare la stima del valore di zona)"
    )


def _reference_payload() -> dict:
    """Espone le tabelle di riferimento in forma serializzabile."""
    return {
        "surface_coefficients": {k.value: v for k, v in reference.SURFACE_COEFFICIENTS.items()},
        "conservation_merit": {k.value: v for k, v in reference.CONSERVATION_MERIT.items()},
        "energy_merit": {k.value: v for k, v in reference.ENERGY_MERIT.items()},
        "heidecke_coefficients": {k.value: v for k, v in reference.HEIDECKE_COEFFICIENTS.items()},
        "construction_cost": {k.value: v for k, v in reference.DEFAULT_CONSTRUCTION_COST.items()},
        "useful_life_years": {k.value: v for k, v in reference.USEFUL_LIFE_YEARS.items()},
        "cap_rate": {k.value: v for k, v in reference.DEFAULT_CAP_RATE.items()},
    }


def create_app() -> FastAPI:
    """Crea e configura l'istanza FastAPI."""
    app = FastAPI(
        title="brickvalue",
        version=__version__,
        description=(
            "Sistema completo per la valutazione di immobili: valore commerciale, "
            "valore di ricostruzione a nuovo, usi bancario, assicurativo e tecnico."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["system"])
    def health() -> dict:
        return {
            "status": "ok",
            "service": "brickvalue",
            "version": __version__,
            "google_maps": is_google_enabled(),
        }

    @app.post("/api/geocode", response_model=GeoLookupResult, tags=["geo"])
    def post_geocode(request: GeocodeRequest) -> GeoLookupResult:
        """Risolve un indirizzo e deduce i parametri di stima (Google Maps + dataset)."""
        return lookup_address(request.address, request.property_type)

    @app.get("/api/geocode/suggest", response_model=SuggestResult, tags=["geo"])
    def get_suggest(q: str = "", limit: int = 5) -> SuggestResult:
        """Autocompletamento dell'indirizzo (Google Places, fallback dataset comuni)."""
        return suggest_addresses(q, limit=limit)

    @app.get("/api/reference", tags=["reference"])
    def get_reference() -> dict:
        return _reference_payload()

    @app.post("/api/surface", response_model=SurfaceResult, tags=["valuation"])
    def post_surface(surface: SurfaceInput) -> SurfaceResult:
        return compute_surface(surface)

    @app.post("/api/valuate", response_model=ValuationReport, tags=["valuation"])
    def post_valuate(request: ValuationRequest) -> ValuationReport:
        try:
            return run_valuation(request)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/valuate/quick", response_model=ValuationReport, tags=["valuation"])
    def post_quick(request: QuickValuationRequest) -> ValuationReport:
        """Valutazione rapida della versione base (input semplificati)."""
        try:
            return run_quick(request)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/condominio", response_model=CondominiumReport, tags=["valuation"])
    def post_condominio(request: CondominiumRequest) -> CondominiumReport:
        """Valore di ricostruzione a nuovo di un condominio con ripartizione per unita'."""
        try:
            return compute_condominium(request)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/valuate/batch", response_model=BatchResult, tags=["valuation"])
    def post_batch(request: BatchValuationRequest) -> BatchResult:
        """Stima massiva di un elenco di immobili (errori isolati per riga)."""
        return compute_batch(request)

    # Frontend statico (se presente)
    if _FRONTEND_DIR.is_dir():
        def _page(name: str) -> FileResponse:
            return FileResponse(_FRONTEND_DIR / name)

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return _page("index.html")

        @app.get("/base", include_in_schema=False)
        def base_page() -> FileResponse:
            return _page("base.html")

        @app.get("/condominio", include_in_schema=False)
        def condo_page() -> FileResponse:
            return _page("condominio.html")

        @app.get("/batch", include_in_schema=False)
        def batch_page() -> FileResponse:
            return _page("batch.html")

        @app.get("/full", include_in_schema=False)
        @app.get("/tecnico", include_in_schema=False)
        def full_page() -> FileResponse:
            return _page("full.html")

        app.mount(
            "/app",
            StaticFiles(directory=str(_FRONTEND_DIR), html=True),
            name="frontend",
        )
    else:  # pragma: no cover - solo se il frontend non e' distribuito
        @app.get("/", include_in_schema=False)
        def index_fallback() -> JSONResponse:
            return JSONResponse(
                {"service": "brickvalue", "docs": "/docs", "version": __version__}
            )

    return app


app = create_app()
