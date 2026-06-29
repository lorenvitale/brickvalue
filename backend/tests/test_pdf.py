"""Test della generazione PDF (skip se WeasyPrint non e' installato)."""

from __future__ import annotations

import pytest

from brickvalue.domain.batch import BatchItem, BatchValuationRequest
from brickvalue.domain.condominium import CondoUnit, CondominiumRequest
from brickvalue.domain.enums import PropertyType
from brickvalue.domain.inputs import MarketInput, ValuationRequest
from brickvalue.domain.property import PropertyInput
from brickvalue.domain.surface import SurfaceComponent, SurfaceInput
from brickvalue.engine.batch import compute_batch
from brickvalue.engine.condominium import compute_condominium
from brickvalue.engine.valuator import valuate
from brickvalue.pdf import batch_html, condominium_html, valuation_html, is_available, to_pdf

pytestmark = pytest.mark.skipif(not is_available(), reason="weasyprint non installato")


def _valuation():
    return valuate(ValuationRequest(
        property=PropertyInput(property_type=PropertyType.APARTMENT, year_built=2000),
        surface=SurfaceInput(components=[SurfaceComponent(type="superficie_principale", area=100)]),
        market=MarketInput(base_unit_value=3000),
    ))


def test_valuation_pdf_bytes():
    pdf = to_pdf(valuation_html(_valuation()))
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 1000


def test_condominium_pdf_bytes():
    rep = compute_condominium(CondominiumRequest(
        units=[CondoUnit(surface_sqm=90, millesimi=500), CondoUnit(surface_sqm=110, millesimi=500)],
        construction_cost_per_sqm=1500, auto_parameters=False,
    ))
    pdf = to_pdf(condominium_html(rep))
    assert pdf[:5] == b"%PDF-"


def test_batch_pdf_bytes():
    res = compute_batch(BatchValuationRequest(items=[
        BatchItem(area_sqm=100, base_unit_value=2000),
        BatchItem(area_sqm=80, address="Milano"),
    ]))
    pdf = to_pdf(batch_html(res))
    assert pdf[:5] == b"%PDF-"


def test_valuation_html_contains_value():
    html = valuation_html(_valuation())
    assert "brickvalue" in html
    assert "Perizia di stima" in html


def test_pdf_endpoint():
    from fastapi.testclient import TestClient

    from brickvalue.api.app import app

    client = TestClient(app)
    payload = {
        "property": {"property_type": "appartamento", "year_built": 2000},
        "surface": {"components": [{"type": "superficie_principale", "area": 100}]},
        "market": {"base_unit_value": 3000},
    }
    r = client.post("/api/valuate/pdf", json=payload)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-"
