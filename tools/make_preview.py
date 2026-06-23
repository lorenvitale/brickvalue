"""Genera un'anteprima HTML autonoma dell'interfaccia brickvalue.

Produce un bundle di pagine (landing, versione base, versione tecnico) navigabili
offline nel browser: CSS e JS sono incorporati e le chiamate API sono simulate da
report reali calcolati dal motore. Apri ``index.html`` del bundle.

Uso::

    python tools/make_preview.py [cartella_output]
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
from brickvalue.domain.property import Location, PropertyInput  # noqa: E402
from brickvalue.domain.quick import BuildingScope, QuickGoal, QuickValuationRequest  # noqa: E402
from brickvalue.domain.surface import SurfaceComponent, SurfaceInput  # noqa: E402
from brickvalue.engine.autofill import lookup_address, run_quick, run_valuation  # noqa: E402
from brickvalue.geo.client import suggest_addresses  # noqa: E402

FRONTEND = ROOT / "frontend"

DEMO_ADDRESS = "Via Dante 1, Milano"


def full_report() -> dict:
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
            location=Location(address=DEMO_ADDRESS),
        ),
        surface=SurfaceInput(
            components=[
                SurfaceComponent(type="superficie_principale", area=95.0),
                SurfaceComponent(type="balcone_scoperto", area=12.0),
                SurfaceComponent(type="cantina_soffitta", area=8.0),
            ]
        ),
        purpose=ValuationPurpose.MARKET,
        cost=CostInput(land_value=60000.0),
        income=IncomeInput(monthly_rent=1100.0),
        reference_year=2026,
    )
    return run_valuation(request).model_dump(mode="json")


def quick_report() -> dict:
    q = QuickValuationRequest(
        goal=QuickGoal.INSURANCE,
        scope=BuildingScope.UNIT,
        area_sqm=100.0,
        year_built=2005,
        address=DEMO_ADDRESS,
    )
    return run_quick(q).model_dump(mode="json")


def geocode_demo() -> dict:
    return lookup_address(DEMO_ADDRESS, PropertyType.APARTMENT).model_dump(mode="json")


def suggest_demo() -> dict:
    return suggest_addresses("Mi", limit=6).model_dump(mode="json")


def _inline_css(html: str) -> str:
    styles = (FRONTEND / "styles.css").read_text(encoding="utf-8")
    return html.replace(
        '<link rel="stylesheet" href="/app/styles.css" />',
        f"<style>\n{styles}\n</style>",
    )


def _relink(html: str) -> str:
    return (
        html.replace('href="/base"', 'href="base.html"')
        .replace('href="/full"', 'href="full.html"')
        .replace('href="/tecnico"', 'href="full.html"')
        .replace('href="/"', 'href="index.html"')
        .replace('href="/docs"', 'href="#"')
    )


def _script(name: str, relink: bool = False) -> str:
    code = (FRONTEND / name).read_text(encoding="utf-8")
    if relink:
        code = code.replace('"/full"', '"full.html"')
    return code


def _stub(full: dict, quick: dict, geo: dict, suggest: dict) -> str:
    return (
        "<script>\n"
        "const __FULL__ = " + json.dumps(full, ensure_ascii=False) + ";\n"
        "const __QUICK__ = " + json.dumps(quick, ensure_ascii=False) + ";\n"
        "const __GEO__ = " + json.dumps(geo, ensure_ascii=False) + ";\n"
        "const __SUGGEST__ = " + json.dumps(suggest, ensure_ascii=False) + ";\n"
        "const __of = window.fetch ? window.fetch.bind(window) : null;\n"
        "window.fetch = (url, opts) => {\n"
        "  const u = String(url);\n"
        "  if (u.includes('/api/geocode/suggest')) return Promise.resolve({ ok:true, json:()=>Promise.resolve(__SUGGEST__) });\n"
        "  if (u.includes('/api/geocode')) return Promise.resolve({ ok:true, json:()=>Promise.resolve(__GEO__) });\n"
        "  if (u.includes('/api/valuate/quick')) return Promise.resolve({ ok:true, json:()=>Promise.resolve(__QUICK__) });\n"
        "  if (u.includes('/api/valuate')) return Promise.resolve({ ok:true, json:()=>Promise.resolve(__FULL__) });\n"
        "  return __of ? __of(url, opts) : Promise.reject(new Error('offline'));\n"
        "};\n"
        "</script>"
    )


def _banner() -> str:
    return (
        '<div style="background:#fffbeb;color:#78350f;text-align:center;'
        'padding:8px;font-size:12.5px;border-bottom:1px solid #fde68a">'
        "Anteprima statica · dati di esempio · l'app reale è interattiva "
        "(<code>python -m brickvalue</code>).</div>"
    )


def build_landing() -> str:
    html = _relink(_inline_css((FRONTEND / "index.html").read_text(encoding="utf-8")))
    return html.replace("<body class=\"landing\">", "<body class=\"landing\">\n  " + _banner())


def build_base(full: dict, quick: dict, geo: dict, suggest: dict) -> str:
    html = _relink(_inline_css((FRONTEND / "base.html").read_text(encoding="utf-8")))
    scripts = (
        _stub(full, quick, geo, suggest)
        + "\n<script>\n" + _script("autocomplete.js") + "\n</script>"
        + "\n<script>\n" + _script("base.js", relink=True) + "\n</script>"
    )
    html = html.replace(
        '<script src="/app/autocomplete.js"></script>\n  <script src="/app/base.js"></script>',
        scripts,
    )
    return html.replace('<body class="base">', '<body class="base">\n  ' + _banner())


def build_full(full: dict, quick: dict, geo: dict, suggest: dict) -> str:
    html = _relink(_inline_css((FRONTEND / "full.html").read_text(encoding="utf-8")))
    scripts = (
        _stub(full, quick, geo, suggest)
        + "\n<script>\n" + _script("render.js") + "\n</script>"
        + "\n<script>\n" + _script("autocomplete.js") + "\n</script>"
        + "\n<script>\n" + _script("app.js") + "\n</script>"
        + "\n<script>window.addEventListener('load', () => { try { loadDemo(); } catch (e) {} });</script>"
    )
    html = html.replace(
        '<script src="/app/render.js"></script>\n  <script src="/app/autocomplete.js"></script>\n  <script src="/app/app.js"></script>',
        scripts,
    )
    return html.replace("<body>", "<body>\n  " + _banner(), 1)


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "preview-out"
    out_dir.mkdir(parents=True, exist_ok=True)

    full = full_report()
    quick = quick_report()
    geo = geocode_demo()
    suggest = suggest_demo()

    (out_dir / "index.html").write_text(build_landing(), encoding="utf-8")
    (out_dir / "base.html").write_text(build_base(full, quick, geo, suggest), encoding="utf-8")
    (out_dir / "full.html").write_text(build_full(full, quick, geo, suggest), encoding="utf-8")

    print(f"Anteprima scritta in: {out_dir} (apri index.html)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
