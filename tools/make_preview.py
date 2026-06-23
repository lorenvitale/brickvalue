"""Genera un'anteprima HTML autonoma dell'interfaccia brickvalue.

L'anteprima incorpora il CSS e la logica di rendering reale dell'app, piu' un
report gia' calcolato dal motore: si apre nel browser senza server ne' API.

Uso::

    python tools/make_preview.py [output.html]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from brickvalue.domain.enums import (  # noqa: E402
    ConservationState,
    EnergyClass,
    PropertyType,
    StructureType,
    ValuationPurpose,
)
from brickvalue.domain.inputs import (  # noqa: E402
    CostInput,
    IncomeInput,
    MarketInput,
    ValuationRequest,
)
from brickvalue.domain.property import PropertyInput  # noqa: E402
from brickvalue.domain.surface import SurfaceComponent, SurfaceInput  # noqa: E402
from brickvalue.engine.valuator import valuate  # noqa: E402

FRONTEND = ROOT / "frontend"


def demo_report() -> dict:
    """Report di esempio (appartamento, finalita' commerciale, 3 metodi)."""
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
            ]
        ),
        purpose=ValuationPurpose.MARKET,
        market=MarketInput(base_unit_value=2800.0),
        cost=CostInput(land_value=60000.0),
        income=IncomeInput(monthly_rent=1100.0),
        reference_year=2026,
    )
    return valuate(request).model_dump(mode="json")


def build_preview() -> str:
    index = (FRONTEND / "index.html").read_text(encoding="utf-8")
    styles = (FRONTEND / "styles.css").read_text(encoding="utf-8")
    render_js = (FRONTEND / "render.js").read_text(encoding="utf-8")
    app_js = (FRONTEND / "app.js").read_text(encoding="utf-8")
    report = demo_report()

    # CSS inline al posto del link
    index = index.replace(
        '<link rel="stylesheet" href="/app/styles.css" />',
        f"<style>\n{styles}\n</style>",
    )

    # Script inline + bootstrap dell'anteprima (riempie il form e mostra il report)
    bootstrap = (
        "<script>\n" + render_js + "\n</script>\n"
        "<script>\n" + app_js + "\n</script>\n"
        "<script>\n"
        "const PREVIEW_REPORT = " + json.dumps(report, ensure_ascii=False) + ";\n"
        "window.addEventListener('load', () => {\n"
        "  try { loadDemo(); } catch (e) { console.error(e); }\n"
        "  try { renderReport(PREVIEW_REPORT); } catch (e) { console.error(e); }\n"
        "});\n"
        "</script>"
    )
    index = index.replace(
        '<script src="/app/render.js"></script>\n  <script src="/app/app.js"></script>',
        bootstrap,
    )

    banner = (
        '<div style="background:#fffbeb;color:#78350f;text-align:center;'
        'padding:8px;font-size:12.5px;border-bottom:1px solid #fde68a">'
        "Anteprima statica generata da dati di esempio — l'app reale è interattiva "
        "(<code>python -m brickvalue</code>).</div>"
    )
    index = index.replace("<body>", "<body>\n  " + banner)
    return index


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "preview.html"
    out.write_text(build_preview(), encoding="utf-8")
    print(f"Anteprima scritta in: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
