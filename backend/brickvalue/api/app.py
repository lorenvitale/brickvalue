"""Applicazione FastAPI che espone il motore di valutazione."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from brickvalue import __version__
from brickvalue.data import reference
from brickvalue.domain.inputs import ValuationRequest
from brickvalue.domain.results import SurfaceResult, ValuationReport
from brickvalue.domain.surface import SurfaceInput
from brickvalue.engine.surface import compute_surface
from brickvalue.engine.valuator import valuate

_FRONTEND_DIR = Path(__file__).resolve().parents[3] / "frontend"


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
        return {"status": "ok", "service": "brickvalue", "version": __version__}

    @app.get("/api/reference", tags=["reference"])
    def get_reference() -> dict:
        return _reference_payload()

    @app.post("/api/surface", response_model=SurfaceResult, tags=["valuation"])
    def post_surface(surface: SurfaceInput) -> SurfaceResult:
        return compute_surface(surface)

    @app.post("/api/valuate", response_model=ValuationReport, tags=["valuation"])
    def post_valuate(request: ValuationRequest) -> ValuationReport:
        try:
            return valuate(request)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Frontend statico (se presente)
    if _FRONTEND_DIR.is_dir():
        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(_FRONTEND_DIR / "index.html")

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
