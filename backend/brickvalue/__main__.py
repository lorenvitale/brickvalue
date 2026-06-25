"""Entry point CLI.

Uso::

    python -m brickvalue              # avvia il server web su http://127.0.0.1:8000
    python -m brickvalue --port 9000  # porta personalizzata
    python -m brickvalue --demo       # stampa una valutazione di esempio (JSON)
"""

from __future__ import annotations

import argparse
import json
import sys


def _demo() -> int:
    """Esegue una valutazione di esempio e ne stampa il report in JSON."""
    from brickvalue.domain.enums import (
        ConservationState,
        EnergyClass,
        PropertyType,
        StructureType,
        ValuationPurpose,
    )
    from brickvalue.domain.inputs import (
        CostInput,
        IncomeInput,
        MarketInput,
        ValuationRequest,
    )
    from brickvalue.domain.property import PropertyInput
    from brickvalue.domain.surface import SurfaceComponent, SurfaceInput
    from brickvalue.engine.valuator import valuate

    request = ValuationRequest(
        property=PropertyInput(
            property_type=PropertyType.APARTMENT,
            structure=StructureType.REINFORCED_CONCRETE,
            conservation=ConservationState.GOOD,
            energy_class=EnergyClass.C,
            year_built=1995,
            floor=3,
            total_floors=5,
            has_elevator=True,
        ),
        surface=SurfaceInput(
            components=[
                SurfaceComponent(type="superficie_principale", area=95.0),
                SurfaceComponent(type="balcone_scoperto", area=12.0),
                SurfaceComponent(type="cantina_soffitta", area=8.0),
            ],
        ),
        purpose=ValuationPurpose.MARKET,
        market=MarketInput(base_unit_value=2800.0),
        cost=CostInput(land_value=60000.0),
        income=IncomeInput(monthly_rent=1100.0),
    )
    report = valuate(request)
    print(json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False))
    return 0


def _serve(host: str, port: int, reload: bool) -> int:
    import uvicorn

    uvicorn.run("brickvalue.api.app:app", host=host, port=port, reload=reload)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brickvalue", description="Sistema di valutazione immobili")
    parser.add_argument("--host", default="127.0.0.1", help="Host del server (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Porta del server (default 8000)")
    parser.add_argument("--reload", action="store_true", help="Auto-reload (sviluppo)")
    parser.add_argument("--demo", action="store_true", help="Stampa una valutazione di esempio")
    args = parser.parse_args(argv)

    if args.demo:
        return _demo()
    return _serve(args.host, args.port, args.reload)


if __name__ == "__main__":
    sys.exit(main())
