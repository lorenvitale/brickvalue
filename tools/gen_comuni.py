"""Genera ``brickvalue/data/comuni.json`` (elenco completo dei comuni italiani).

Dipendenze di sviluppo (non runtime)::

    pip install italy-geopop pyarrow

Estrae nome, provincia (sigla), regione, un centro rappresentativo (punto medio
del bounding box dei poligoni ISTAT) e la popolazione per tutti i ~7.900 comuni.
La popolazione serve a ordinare i suggerimenti per rilevanza.

Uso::

    python tools/gen_comuni.py
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "backend" / "brickvalue" / "data" / "comuni.json"


def _vertices(wkb: bytes):
    """Itera i vertici (x, y) di una geometria WKB (Multi)Polygon/Point/Line."""
    i = 0

    def u32(fmt: str) -> int:
        nonlocal i
        (v,) = struct.unpack_from(fmt + "I", wkb, i)
        i += 4
        return v

    def geom():
        nonlocal i
        order = wkb[i]
        i += 1
        fmt = "<" if order == 1 else ">"
        typ = u32(fmt)
        base = typ & 0xFF
        if typ & 0x20000000:  # flag SRID
            i += 4
        if base == 1:  # point
            x, y = struct.unpack_from(fmt + "dd", wkb, i)
            i += 16
            yield x, y
        elif base == 2:  # linestring
            for _ in range(u32(fmt)):
                x, y = struct.unpack_from(fmt + "dd", wkb, i)
                i += 16
                yield x, y
        elif base == 3:  # polygon
            for _ in range(u32(fmt)):
                for _ in range(u32(fmt)):
                    x, y = struct.unpack_from(fmt + "dd", wkb, i)
                    i += 16
                    yield x, y
        elif base in (4, 5, 6, 7):  # multi* / collection
            for _ in range(u32(fmt)):
                yield from geom()

    yield from geom()


def _center(wkb: bytes) -> tuple[float, float]:
    minx = miny = 1e18
    maxx = maxy = -1e18
    for x, y in _vertices(wkb):
        minx, maxx = min(minx, x), max(maxx, x)
        miny, maxy = min(miny, y), max(maxy, y)
    return round((minx + maxx) / 2, 4), round((miny + maxy) / 2, 4)


def main() -> int:
    import pyarrow.feather as feather
    from italy_geopop import data  # type: ignore

    data_dir = Path(data.__file__).resolve().parent if hasattr(data, "__file__") else None
    # In alternativa il percorso dei dati e' nel package italy_geopop/data
    import italy_geopop

    base = Path(italy_geopop.__file__).resolve().parent / "data"
    muni = feather.read_table(base / "2023_italy_municipalities.feather").to_pylist()
    geo = feather.read_table(base / "2023_italy_geo_municipalities.feather").to_pylist()
    pop = feather.read_table(base / "2023_italy_pop.feather").to_pylist()
    geomap = {g["municipality_code"]: g["geometry"] for g in geo}

    popmap: dict[str, int] = {}
    for r in pop:  # righe per fascia d'eta': sommiamo il totale per comune
        code = str(r["municipality_code"])
        popmap[code] = popmap.get(code, 0) + (r["tot"] or 0)

    rows = []
    for m in muni:
        wkb = geomap.get(m["municipality_code"])
        lon, lat = _center(wkb) if wkb else (None, None)
        rows.append([
            m["municipality"], m["province_short"], m["region"], lat, lon,
            popmap.get(str(m["municipality_code"]), 0),
        ])

    OUT.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Scritti {len(rows)} comuni in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
