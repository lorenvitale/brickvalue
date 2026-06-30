"""Test di geolocalizzazione, inferenza dei parametri e autofill."""

from __future__ import annotations

import pytest

from brickvalue.data.market_reference import (
    centrality_multiplier,
    find_city_in_text,
    haversine_km,
    normalize,
    resolve_region,
    suggest_cities,
)
from brickvalue.domain.enums import PropertyType, ValuationPurpose
from brickvalue.domain.geo import GeoLocation
from brickvalue.domain.inputs import MarketInput, ValuationRequest
from brickvalue.domain.property import Location, PropertyInput
from brickvalue.domain.quick import BuildingScope, QuickGoal, QuickValuationRequest
from brickvalue.domain.surface import SurfaceComponent, SurfaceInput
from brickvalue.engine.autofill import enrich_request, lookup_address, run_quick
from brickvalue.engine.inference import infer_parameters
from brickvalue.geo.client import (
    GeoError,
    autocomplete,
    geocode,
    resolve_location,
    suggest_addresses,
)


# --------------------------------------------------------------------------
# Dataset / utility
# --------------------------------------------------------------------------
def test_normalize():
    assert normalize("Sant'Angelo (MI)") == "sant angelo mi"
    assert normalize("Reggio Emilia") == "reggio emilia"


def test_find_city_distinguishes_reggio():
    # Riconosce le forme correnti mappandole sui nomi ufficiali ISTAT
    assert find_city_in_text("Via Roma, Reggio Emilia") == "Reggio nell'Emilia"
    assert find_city_in_text("Reggio Calabria, lungomare") == "Reggio di Calabria"


def test_find_city_word_boundary():
    # "Como" non deve matchare dentro un'altra parola
    assert find_city_in_text("Comodoro 1, Roma") == "Roma"


def test_find_small_town():
    # Il fix principale: anche i piccoli comuni vengono riconosciuti
    assert find_city_in_text("Via Garibaldi 3, Desenzano del Garda") == "Desenzano del Garda"


def test_lookup_place_alias_and_bilingual():
    from brickvalue.data.market_reference import lookup_place
    assert lookup_place("Bolzano").region == "Trentino-Alto Adige"
    assert lookup_place("Reggio Emilia").name == "Reggio nell'Emilia"
    assert lookup_place("Desenzano del Garda").region == "Lombardia"


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


def test_infer_market_rent_estimated():
    loc = GeoLocation(query="Milano", source="fallback_testuale", municipality="Milano",
                      region="Lombardia")
    p = infer_parameters(loc, PropertyType.APARTMENT)
    # 4900 * 0.045 / 12 = 18.375
    assert p.market_rent_sqm_month == pytest.approx(18.38, abs=0.05)


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


# --------------------------------------------------------------------------
# Autocompletamento
# --------------------------------------------------------------------------
def test_suggest_cities_prefix_and_contains():
    names = [p.name for p in suggest_cities("mil", 8)]
    assert "Milano" in names
    reggio = [p.name for p in suggest_cities("reggio", 8)]
    assert any("Emilia" in n for n in reggio)
    assert any("Calabria" in n for n in reggio)


def test_suggest_cities_small_town():
    names = [p.name for p in suggest_cities("desenz", 5)]
    assert "Desenzano del Garda" in names


def test_suggest_ranks_major_city_first():
    # Le grandi citta' devono comparire per prime (ordinamento per popolazione)
    assert suggest_cities("mil", 6)[0].name == "Milano"
    assert suggest_cities("fir", 6)[0].name == "Firenze"
    assert suggest_cities("roma", 6)[0].name == "Roma"
    assert suggest_cities("napoli", 6)[0].name == "Napoli"


def test_suggest_no_midword_match():
    # "reggio" non deve restituire match a meta' parola (Greggio, Bareggio, ...)
    names = [p.name for p in suggest_cities("reggio", 12)]
    assert "Greggio" not in names
    assert "Bareggio" not in names
    assert any("Reggio" in n for n in names)


def test_suggest_address_with_street():
    # "via roma, mil" deve comunque proporre Milano (ultima parola = comune)
    assert "Milano" in [p.name for p in suggest_cities("via roma, mil", 6)]


def test_suggest_cities_empty():
    assert suggest_cities("", 5) == []


def test_autocomplete_requires_key():
    with pytest.raises(GeoError):
        autocomplete("Mil")


def _fake_predictions(url, params, timeout):
    return {
        "status": "OK",
        "predictions": [
            {"description": "Via Roma, Milano MI, Italia", "place_id": "p1"},
            {"description": "Via Roma, Monza MB, Italia", "place_id": "p2"},
        ],
    }


def test_autocomplete_parses_predictions():
    out = autocomplete("Via Roma", api_key="TEST", fetch=_fake_predictions)
    assert len(out) == 2
    assert out[0].description.startswith("Via Roma")
    assert out[0].place_id == "p1"
    assert out[0].source == "google"


def test_autocomplete_limit():
    out = autocomplete("Via Roma", api_key="TEST", fetch=_fake_predictions, limit=1)
    assert len(out) == 1


def test_suggest_addresses_google():
    res = suggest_addresses("Via Roma", api_key="TEST", fetch=_fake_predictions)
    assert res.source == "google"
    assert len(res.suggestions) == 2


def test_suggest_addresses_fallback_dataset():
    res = suggest_addresses("Tori")  # nessuna chiave -> dataset
    assert res.source == "dataset"
    assert any(s.municipality == "Torino" for s in res.suggestions)


def test_suggest_addresses_no_match():
    res = suggest_addresses("zzzqqq")
    assert res.source == "nessuna"
    assert res.suggestions == []


# --------------------------------------------------------------------------
# Photon (suggerimenti a livello di via, gratuito)
# --------------------------------------------------------------------------
def _fake_photon(url, params, timeout):
    return {"features": [
        {"properties": {"name": "Piazza Vanvitelli", "city": "Napoli",
                        "state": "Campania", "countrycode": "IT"}},
        {"properties": {"street": "Via Roma", "housenumber": "10",
                        "city": "Napoli", "countrycode": "IT"}},
        {"properties": {"name": "Vanvitelli", "city": "Wien", "countrycode": "AT"}},
    ]}


def test_photon_autocomplete_parses_and_filters():
    from brickvalue.geo.client import photon_autocomplete

    out = photon_autocomplete("piazza vanvitelli 1 napoli", fetch=_fake_photon)
    descs = [s.description for s in out]
    assert "Piazza Vanvitelli, Napoli" in descs
    assert "Via Roma 10, Napoli" in descs
    assert all(s.source == "photon" for s in out)
    # la voce estera (Wien, AT) e' esclusa
    assert not any("Wien" in d for d in descs)


def test_suggest_addresses_uses_photon():
    res = suggest_addresses("piazza vanvitelli 1 napoli", fetch=_fake_photon)
    assert res.source == "photon"
    assert any("Vanvitelli" in s.description for s in res.suggestions)


def test_suggest_addresses_photon_failure_falls_back_to_dataset():
    def _boom(url, params, timeout):
        raise RuntimeError("offline")

    res = suggest_addresses("Torino", fetch=_boom)
    assert res.source == "dataset"
    assert any(s.municipality == "Torino" for s in res.suggestions)
