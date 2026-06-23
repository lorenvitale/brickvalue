"""Test dell'API REST."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from brickvalue.api.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_reference(client: TestClient):
    r = client.get("/api/reference")
    assert r.status_code == 200
    data = r.json()
    assert "surface_coefficients" in data
    assert data["surface_coefficients"]["superficie_principale"] == 1.0
    assert "cap_rate" in data


def test_surface_endpoint(client: TestClient):
    payload = {
        "components": [
            {"type": "superficie_principale", "area": 100.0},
            {"type": "balcone_scoperto", "area": 10.0},
        ]
    }
    r = client.post("/api/surface", json=payload)
    assert r.status_code == 200
    assert r.json()["commercial_surface"] == pytest.approx(103.0)


def test_valuate_endpoint(client: TestClient):
    payload = {
        "property": {
            "property_type": "appartamento",
            "conservation": "buono",
            "energy_class": "C",
            "year_built": 2000,
            "floor": 3,
            "total_floors": 5,
            "has_elevator": True,
        },
        "surface": {
            "components": [
                {"type": "superficie_principale", "area": 90.0},
                {"type": "balcone_scoperto", "area": 8.0},
            ]
        },
        "purpose": "commerciale",
        "market": {"base_unit_value": 2500.0},
        "cost": {"land_value": 40000.0},
        "income": {"monthly_rent": 950.0},
    }
    r = client.post("/api/valuate", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["market_value"] > 0
    assert data["reconstruction_value_new"] is not None
    assert data["recommended_value_label"]


def test_valuate_validation_error_422(client: TestClient):
    # market senza base_unit_value ne' comparables -> errore di validazione Pydantic
    payload = {
        "property": {"property_type": "appartamento"},
        "surface": {"components": [{"type": "superficie_principale", "area": 90.0}]},
        "market": {},
    }
    r = client.post("/api/valuate", json=payload)
    assert r.status_code == 422


def test_valuate_engine_error_422(client: TestClient):
    # Terreno con finalita' assicurativa e nessun dato di mercato -> dati insufficienti
    payload = {
        "property": {"property_type": "terreno_edificabile"},
        "surface": {"components": [{"type": "superficie_principale", "area": 500.0}]},
        "purpose": "assicurativo",
    }
    r = client.post("/api/valuate", json=payload)
    assert r.status_code == 422


def test_root_serves_frontend(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_openapi_available(client: TestClient):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert "/api/valuate" in r.json()["paths"]


def test_quick_endpoint_insurance(client: TestClient):
    payload = {
        "goal": "assicurazione",
        "scope": "unita",
        "area_sqm": 100,
        "year_built": 2005,
        "condition": "buono",
    }
    r = client.post("/api/valuate/quick", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["reconstruction_value_new"] is not None
    assert data["recommended_value"] == data["reconstruction_value_new"]


def test_quick_endpoint_validation_422(client: TestClient):
    # vendita senza prezzo di zona -> errore di validazione
    r = client.post("/api/valuate/quick", json={"goal": "vendita", "area_sqm": 90})
    assert r.status_code == 422


def test_quick_huge_building_is_422_not_500(client: TestClient):
    r = client.post(
        "/api/valuate/quick",
        json={"goal": "assicurazione", "scope": "edificio", "num_units": 5000, "avg_unit_sqm": 1000},
    )
    assert r.status_code == 422


def test_base_and_full_pages(client: TestClient):
    for path in ("/", "/base", "/full", "/tecnico"):
        r = client.get(path)
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]


def test_geocode_endpoint(client: TestClient):
    r = client.post("/api/geocode", json={"address": "Via Roma, Milano"})
    assert r.status_code == 200
    data = r.json()
    assert data["location"]["municipality"] == "Milano"
    assert data["parameters"]["base_unit_value"] == 4900.0


def test_valuate_autofills_from_address(client: TestClient):
    payload = {
        "property": {
            "property_type": "appartamento",
            "location": {"address": "Corso Italia, Napoli"},
        },
        "surface": {"components": [{"type": "superficie_principale", "area": 100}]},
        "purpose": "commerciale",
    }
    r = client.post("/api/valuate", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["geo"] is not None
    assert data["geo"]["parameters"]["city"] == "Napoli"
    assert data["market"] is not None  # valore di zona dedotto
    assert data["market_value"] > 0


def test_health_reports_google_flag(client: TestClient):
    r = client.get("/api/health")
    assert "google_maps" in r.json()
