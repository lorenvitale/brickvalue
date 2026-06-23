"""Test di geolocalizzazione, inferenza dei parametri e autofill."""

from __future__ import annotations

import pytest

from brickvalue.data.market_reference import (
    centrality_multiplier,
    find_city_in_text,
    haversine_km,
    normalize,
    resolve_region,
)
from brickvalue.domain.enums import PropertyType, ValuationPurpose
from brickvalue.domain.geo import GeoLocation
from brickvalue.domain.inputs import MarketInput, ValuationRequest
from brickvalue.domain.property import Location, PropertyInput
from brickvalue.domain.quick import BuildingScope, QuickGoal, QuickValuationRequest
from brickvalue.domain.surface import SurfaceComponent, SurfaceInput
from brickvalue.engine.autofill import enrich_request, lookup_address, run_quick
from brickvalue.engine.inference import infer_parameters
from brickvalue.geo.client import GeoError, geocode, resolve_location


# --------------------------------------------------------------------------
# Dataset / utility
# --------------------------------------------------------------------------
def test_normalize():
    assert normalize("Sant'Angelo (MI)") == "sant angelo mi"
    assert normalize("Reggio Emilia") == "reggio emilia"


def test_find_city_distinguishes_reggio():
    assert find_city_in_text("Via Roma, Reggio Emilia") == "Reggio Emilia"
    assert find_city_in_text("Reggio Calabria, lungomare") == "Reggio Calabria"


def test_find_city_word_boundary():
    # "Como" non deve matchare dentro un'altra parola
    assert find_city_in_text("Comodoro 1, Roma") == "Roma"


def test_resolve_region_bilingual():
    assert resolve_region("Trentino-Alto Adige/Südtirol") == "Trentino-Alto Adige"
    assert resolve_region("Lombardia") == "Lombardia"
    assert resolve_region("Inventata") is None


def test_haversine_and_centrality():
    assert haversine_km(45.4642, 9.19, 45.4642, 9.19) == pytest.approx(0.0, abs=1e-6)
    assert centrality_multiplier(0.5) == 1.30
    assert centrality_multiplier(15.0) == 0.82


# --------------------------------------------------------------------------
# Inferenza
# --------------------------------------------------------------------------
def test_infer_city_fallback():
    loc = GeoLocation(query="Milano", source="fallback_testuale", municipality="Milano",
                      province="MI", region="Lombardia")
    p = infer_parameters(loc)
    assert p.base_unit_value == 4900.0  # nessuna centralita' senza coordinate
    assert p.city == "Milano"
    assert p.cap_rate == 0.030
    assert p.construction_cost_multiplier == pytest.approx(1.08)
    assert p.confidence == "media"


def test_infer_region_only():
    loc = GeoLocation(query="x", source="google", region="Sicilia")
    p = infer_parameters(loc)
    assert p.base_unit_value == 1300.0  # media regionale Sicilia
    assert p.confidence == "media"


def test_infer_unknown_national_default():
    loc = GeoLocation(query="x", source="sconosciuto")
    p = infer_parameters(loc)
    assert p.base_unit_value == 1700.0
    assert p.confidence == "bassa"


def test_infer_centrality_central_vs_peripheral():
    central = GeoLocation(query="x", source="google", municipality="Milano",
                          region="Lombardia", lat=45.4654, lng=9.1866)
    far = GeoLocation(query="x", source="google", municipality="Milano",
                      region="Lombardia", lat=45.5600, lng=9.1000)
    pc = infer_parameters(central)
    pf = infer_parameters(far)
    assert pc.base_unit_value > 4900.0   # centro -> premio
    assert pf.base_unit_value < 4900.0   # periferia -> sconto
    assert pc.confidence == "alta"


# --------------------------------------------------------------------------
# Client geocode (con fetch iniettato)
# --------------------------------------------------------------------------
def _fake_google(lat=45.4654, lng=9.1866):
    def _fetch(url, params, timeout):
        return {
            "status": "OK",
            "results": [{
                "formatted_address": "Via Roma, 20121 Milano MI, Italia",
                "geometry": {"location": {"lat": lat, "lng": lng}, "location_type": "ROOFTOP"},
                "address_components": [
                    {"long_name": "Milano", "short_name": "Milano",
                     "types": ["administrative_area_level_3", "locality"]},
                    {"long_name": "Milano", "short_name": "MI",
                     "types": ["administrative_area_level_2"]},
                    {"long_name": "Lombardia", "short_name": "Lombardia",
                     "types": ["administrative_area_level_1"]},
                    {"long_name": "20121", "types": ["postal_code"]},
                ],
                "partial_match": False,
            }],
        }
    return _fetch


def test_geocode_requires_key():
    with pytest.raises(GeoError):
        geocode("Milano")  # nessuna chiave in ambiente di test


def test_geocode_parses_google_response():
    loc = geocode("Milano", api_key="TEST", fetch=_fake_google())
    assert loc.source == "google"
    assert loc.municipality == "Milano"
    assert loc.province == "MI"
    assert loc.region == "Lombardia"
    assert loc.lat == pytest.approx(45.4654)
    assert loc.location_type == "ROOFTOP"


def test_geocode_zero_results_raises():
    def _empty(url, params, timeout):
        return {"status": "ZERO_RESULTS", "results": []}
    with pytest.raises(GeoError):
        geocode("xyz", api_key="TEST", fetch=_empty)


def test_resolve_location_falls_back_on_error():
    def _boom(url, params, timeout):
        raise RuntimeError("rete giu'")
    loc = resolve_location("Via Dante, Torino", api_key="TEST", fetch=_boom)
    assert loc.source == "fallback_testuale"
    assert loc.municipality == "Torino"


# --------------------------------------------------------------------------
# Autofill / enrichment
# --------------------------------------------------------------------------
def _request_with_address(address, **kw):
    prop = PropertyInput(property_type=PropertyType.APARTMENT, location=Location(address=address))
    surface = SurfaceInput(components=[SurfaceComponent(type="superficie_principale", area=100)])
    return ValuationRequest(property=prop, surface=surface, **kw)


def test_enrich_sets_market_from_address():
    req = _request_with_address("Via Po, Torino")
    enriched, lookup = enrich_request(req)
    assert lookup is not None
    assert enriched.market is not None
    assert enriched.market.base_unit_value == 1900.0  # Torino


def test_enrich_respects_explicit_market():
    req = _request_with_address("Via Po, Torino", market=MarketInput(base_unit_value=9999))
    enriched, _ = enrich_request(req)
    assert enriched.market.base_unit_value == 9999  # non sovrascritto


def test_enrich_disabled():
    req = _request_with_address("Via Po, Torino", auto_parameters=False)
    enriched, lookup = enrich_request(req)
    assert lookup is None
    assert enriched.market is None


def test_enrich_no_address():
    prop = PropertyInput(property_type=PropertyType.APARTMENT)
    surface = SurfaceInput(components=[SurfaceComponent(type="superficie_principale", area=100)])
    req = ValuationRequest(property=prop, surface=surface)
    _, lookup = enrich_request(req)
    assert lookup is None


def test_run_quick_market_via_address():
    q = QuickValuationRequest(
        goal=QuickGoal.MARKET, scope=BuildingScope.UNIT, area_sqm=80, address="Firenze centro"
    )
    report = run_quick(q)
    assert report.geo is not None
    assert report.geo.parameters.city == "Firenze"
    assert report.market_value > 0


def test_quick_market_address_instead_of_price_is_valid():
    # Non solleva: l'indirizzo sostituisce il prezzo
    QuickValuationRequest(goal=QuickGoal.MARKET, area_sqm=90, address="Bologna")


def test_lookup_google_centrality(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "TEST")
    res = lookup_address("Duomo, Milano", PropertyType.APARTMENT, fetch=_fake_google())
    assert res.location.source == "google"
    assert res.parameters.centrality_multiplier == 1.30
    assert res.parameters.base_unit_value == pytest.approx(4900 * 1.30)
    assert res.parameters.confidence == "alta"
