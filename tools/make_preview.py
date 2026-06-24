"""Genera un'anteprima HTML autonoma dell'interfaccia brickvalue.

Produce un bundle di pagine (landing, base, condominio, tecnico) navigabili
offline nel browser: CSS e JS sono incorporati e le chiamate API sono simulate
da report reali calcolati dal motore. Apri ``index.html`` del bundle.

Uso::

    python tools/make_preview.py [cartella_output]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from brickvalue.domain.condominium import CondoUnit, CondominiumRequest  # noqa: E402
from brickvalue.domain.enums import (  # noqa: E402
    ConservationState,
    EnergyClass,
    PropertyType,
    StructureType,
    ValuationPurpose,
)
from brickvalue.domain.inputs import CostInput, IncomeInput, ValuationRequest  # noqa: E402
from brickvalue.domain.property import Location, PropertyInput  # noqa: E402
from brickvalue.domain.quick import BuildingScope, QuickGoal, QuickValuationRequest  # noqa: E402
from brickvalue.domain.surface import SurfaceComponent, SurfaceInput  # noqa: E402
from brickvalue.engine.autofill import lookup_address, run_quick, run_valuation  # noqa: E402
from brickvalue.engine.condominium import compute_condominium  # noqa: E402
from brickvalue.geo.client import suggest_addresses  # noqa: E402

FRONTEND = ROOT / "frontend"
DEMO_ADDRESS = "Via Dante 1, Milano"


# --------------------------------------------------------------------------- #
# Report di esempio
# --------------------------------------------------------------------------- #
def full_report() -> dict:
    request = ValuationRequest(
        property=PropertyInput(
            property_type=PropertyType.APARTMENT,
            structure=StructureType.REINFORCED_CONCRETE,
            conservation=ConservationState.GOOD,
            energy_class=EnergyClass.C,
            year_built=1995, floor=3, total_floors=5, has_elevator=True,
            location=Location(address=DEMO_ADDRESS),
        ),
        surface=SurfaceInput(components=[
            SurfaceComponent(type="superficie_principale", area=95.0),
            SurfaceComponent(type="balcone_scoperto", area=12.0),
            SurfaceComponent(type="cantina_soffitta", area=8.0),
        ]),
        purpose=ValuationPurpose.MARKET,
        cost=CostInput(land_value=60000.0),
        income=IncomeInput(monthly_rent=1100.0),
        reference_year=2026,
    )
    return run_valuation(request).model_dump(mode="json")


def quick_report() -> dict:
    q = QuickValuationRequest(
        goal=QuickGoal.INSURANCE, scope=BuildingScope.UNIT,
        area_sqm=100.0, year_built=2005, address=DEMO_ADDRESS,
    )
    return run_quick(q).model_dump(mode="json")


def condo_report() -> dict:
    req = CondominiumRequest(
        address="Via Roma 10, Brescia",
        common_area_sqm=120,
        units=[
            CondoUnit(label="Scala A - Int 1", surface_sqm=85, millesimi=180),
            CondoUnit(label="Scala A - Int 2", surface_sqm=95, millesimi=210),
            CondoUnit(label="Scala A - Int 3", surface_sqm=110, millesimi=250),
            CondoUnit(label="Scala B - Int 4", surface_sqm=75, millesimi=160),
            CondoUnit(label="Scala B - Int 5", surface_sqm=90, millesimi=200),
        ],
    )
    return compute_condominium(req).model_dump(mode="json")


def geocode_demo() -> dict:
    return lookup_address(DEMO_ADDRESS, PropertyType.APARTMENT).model_dump(mode="json")


def suggest_demo() -> dict:
    return suggest_addresses("Mi", limit=6).model_dump(mode="json")


# --------------------------------------------------------------------------- #
# Inlining
# --------------------------------------------------------------------------- #
def _inline_css(html: str) -> str:
    styles = (FRONTEND / "styles.css").read_text(encoding="utf-8")
    return html.replace(
        '<link rel="stylesheet" href="/app/styles.css" />', f"<style>\n{styles}\n</style>"
    )


def _relink(html: str) -> str:
    return (
        html.replace('href="/base"', 'href="base.html"')
        .replace('href="/full"', 'href="full.html"')
        .replace('href="/tecnico"', 'href="full.html"')
        .replace('href="/condominio"', 'href="condominio.html"')
        .replace('href="/"', 'href="index.html"')
        .replace('href="/docs"', 'href="#"')
    )


def _script(name: str) -> str:
    code = (FRONTEND / name).read_text(encoding="utf-8")
    return code.replace('"/full"', '"full.html"')


def _stub(data: dict) -> str:
    js = ";\n".join(f"const {k} = {json.dumps(v, ensure_ascii=False)}" for k, v in data.items())
    return f"""<script>
{js};
const __of = window.fetch ? window.fetch.bind(window) : null;
window.fetch = (url, opts) => {{
  const u = String(url);
  if (u.includes('/api/geocode/suggest')) return Promise.resolve({{ ok:true, json:()=>Promise.resolve(__SUGGEST__) }});
  if (u.includes('/api/geocode')) return Promise.resolve({{ ok:true, json:()=>Promise.resolve(__GEO__) }});
  if (u.includes('/api/condominio')) return Promise.resolve({{ ok:true, json:()=>Promise.resolve(__CONDO__) }});
  if (u.includes('/api/valuate/quick')) return Promise.resolve({{ ok:true, json:()=>Promise.resolve(__QUICK__) }});
  if (u.includes('/api/valuate')) return Promise.resolve({{ ok:true, json:()=>Promise.resolve(__FULL__) }});
  return __of ? __of(url, opts) : Promise.reject(new Error('offline'));
}};
</script>"""


def _banner() -> str:
    return (
        '<div style="background:#fffbeb;color:#78350f;text-align:center;'
        'padding:8px;font-size:12.5px;border-bottom:1px solid #fde68a">'
        "Anteprima statica · dati di esempio · l'app reale è interattiva "
        "(<code>python -m brickvalue</code>).</div>"
    )


_SCRIPT_RE = re.compile(r'<script src="/app/([\w.]+)"></script>')


def build_page(filename: str, stub_data: dict, body_class: str, tail: str = "") -> str:
    html = _relink(_inline_css((FRONTEND / filename).read_text(encoding="utf-8")))
    names = _SCRIPT_RE.findall(html)
    html = _SCRIPT_RE.sub("", html)
    parts = [_stub(stub_data)]
    parts += [f"<script>\n{_script(n)}\n</script>" for n in names]
    if tail:
        parts.append(tail)
    html = html.replace("</body>", "\n".join(parts) + "\n</body>")
    marker = f'<body class="{body_class}">' if body_class else "<body>"
    return html.replace(marker, marker + "\n  " + _banner(), 1)


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "preview-out"
    out_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "__FULL__": full_report(),
        "__QUICK__": quick_report(),
        "__CONDO__": condo_report(),
        "__GEO__": geocode_demo(),
        "__SUGGEST__": suggest_demo(),
    }
    prefill = "<script>window.addEventListener('load',()=>{try{loadDemo();}catch(e){}});</script>"

    (out_dir / "index.html").write_text(build_page("index.html", data, "landing"), encoding="utf-8")
    (out_dir / "base.html").write_text(build_page("base.html", data, "base"), encoding="utf-8")
    (out_dir / "condominio.html").write_text(
        build_page("condominio.html", data, "", prefill), encoding="utf-8"
    )
    (out_dir / "full.html").write_text(
        build_page("full.html", data, "", prefill), encoding="utf-8"
    )

    print(f"Anteprima scritta in: {out_dir} (apri index.html)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
