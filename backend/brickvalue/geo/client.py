"""Client di geocodifica.

Usa l'API Google Maps Geocoding quando e' configurata la variabile d'ambiente
``GOOGLE_MAPS_API_KEY``; in assenza di chiave (o in caso di errore) ricade su un
riconoscimento testuale del comune basato sul dataset di riferimento.

Il client e' iniettabile (parametro ``fetch``) per consentire i test senza rete.
"""

from __future__ import annotations

import os
from typing import Callable

from brickvalue.data.market_reference import find_place_in_text, suggest_cities
from brickvalue.domain.geo import AddressSuggestion, GeoLocation, SuggestResult

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
AUTOCOMPLETE_URL = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
# Photon (OpenStreetMap, Komoot): autocompletamento indirizzi gratuito, senza chiave.
PHOTON_URL = "https://photon.komoot.io/api/"

Fetcher = Callable[[str, dict, float], dict]


class GeoError(Exception):
    """Errore di geocodifica (chiave assente, rete, risposta non valida)."""


def is_google_enabled() -> bool:
    """True se e' configurata una chiave API Google Maps."""
    return bool(os.environ.get("GOOGLE_MAPS_API_KEY"))


def _ca_verify():
    """Percorso del bundle CA da usare per HTTPS attraverso il proxy d'ambiente."""
    for var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        path = os.environ.get(var)
        if path and os.path.exists(path):
            return path
    default = "/root/.ccr/ca-bundle.crt"
    return default if os.path.exists(default) else True


def _default_fetch(url: str, params: dict, timeout: float) -> dict:
    import httpx

    with httpx.Client(timeout=timeout, verify=_ca_verify(), trust_env=True) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def _parse_components(components: list[dict]) -> dict:
    out: dict[str, str] = {}
    for c in components:
        types = c.get("types", [])
        if "administrative_area_level_3" in types or "locality" in types:
            out.setdefault("municipality", c.get("long_name"))
        if "administrative_area_level_2" in types:
            out["province"] = c.get("short_name")
        if "administrative_area_level_1" in types:
            out["region"] = c.get("long_name")
        if "postal_code" in types:
            out["postal_code"] = c.get("long_name")
    return out


def geocode(
    address: str,
    *,
    api_key: str | None = None,
    timeout: float = 10.0,
    fetch: Fetcher | None = None,
) -> GeoLocation:
    """Geocodifica un indirizzo con Google Maps. Solleva :class:`GeoError` in caso di problemi."""
    key = api_key or os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        raise GeoError("GOOGLE_MAPS_API_KEY non configurata")
    if not address or not address.strip():
        raise GeoError("Indirizzo vuoto")

    do_fetch = fetch or _default_fetch
    try:
        data = do_fetch(
            GEOCODE_URL,
            {"address": address, "key": key, "region": "it", "language": "it"},
            timeout,
        )
    except GeoError:
        raise
    except Exception as exc:  # rete, timeout, json non valido
        raise GeoError(f"Errore di rete nella geocodifica: {exc}") from exc

    status = data.get("status")
    if status != "OK" or not data.get("results"):
        raise GeoError(f"Geocoding non riuscito ({status} {data.get('error_message', '')})".strip())

    res = data["results"][0]
    loc = res.get("geometry", {}).get("location", {})
    comp = _parse_components(res.get("address_components", []))
    return GeoLocation(
        query=address,
        source="google",
        formatted_address=res.get("formatted_address"),
        municipality=comp.get("municipality"),
        province=comp.get("province"),
        region=comp.get("region"),
        postal_code=comp.get("postal_code"),
        lat=loc.get("lat"),
        lng=loc.get("lng"),
        location_type=res.get("geometry", {}).get("location_type"),
        partial_match=bool(res.get("partial_match", False)),
    )


def resolve_location(
    address: str,
    *,
    api_key: str | None = None,
    fetch: Fetcher | None = None,
) -> GeoLocation:
    """Risolve un indirizzo: prima Google, poi fallback testuale sul dataset.

    Non solleva mai: in caso di impossibilita' restituisce una localizzazione con
    ``source='sconosciuto'``.
    """
    if api_key or is_google_enabled() or fetch is not None:
        try:
            return geocode(address, api_key=api_key, fetch=fetch)
        except GeoError:
            pass

    place = find_place_in_text(address or "")
    if place:
        return GeoLocation(
            query=address,
            source="fallback_testuale",
            municipality=place.name,
            province=place.prov,
            region=place.region,
        )
    return GeoLocation(query=address, source="sconosciuto")


def autocomplete(
    query: str,
    *,
    api_key: str | None = None,
    timeout: float = 10.0,
    fetch: Fetcher | None = None,
    limit: int = 5,
) -> list[AddressSuggestion]:
    """Suggerimenti di indirizzo via Google Places. Solleva :class:`GeoError` se non disponibile."""
    key = api_key or os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        raise GeoError("GOOGLE_MAPS_API_KEY non configurata")
    if not query or not query.strip():
        return []

    do_fetch = fetch or _default_fetch
    try:
        data = do_fetch(
            AUTOCOMPLETE_URL,
            {"input": query, "key": key, "language": "it", "components": "country:it"},
            timeout,
        )
    except GeoError:
        raise
    except Exception as exc:
        raise GeoError(f"Errore di rete nell'autocompletamento: {exc}") from exc

    status = data.get("status")
    if status not in ("OK", "ZERO_RESULTS"):
        raise GeoError(f"Autocompletamento non riuscito ({status})")

    out: list[AddressSuggestion] = []
    for pred in data.get("predictions", [])[:limit]:
        desc = pred.get("description")
        if desc:
            out.append(
                AddressSuggestion(description=desc, place_id=pred.get("place_id"), source="google")
            )
    return out


def _photon_description(props: dict) -> str | None:
    """Costruisce una descrizione leggibile da una feature Photon (solo Italia)."""
    street = props.get("street")
    housenumber = props.get("housenumber")
    name = props.get("name")
    city = props.get("city") or props.get("county") or props.get("state")
    if street:
        line = f"{street} {housenumber}".strip() if housenumber else street
    else:
        line = name
    parts = [p for p in (line, city) if p]
    if not parts:
        return None
    if len(parts) == 2 and parts[0] == parts[1]:
        parts = [parts[0]]
    return ", ".join(parts)


def photon_autocomplete(
    query: str,
    *,
    timeout: float = 3.0,
    fetch: Fetcher | None = None,
    limit: int = 5,
) -> list[AddressSuggestion]:
    """Suggerimenti a livello di via via Photon (gratuito). Solleva GeoError se non raggiungibile."""
    if not query or not query.strip():
        return []
    do_fetch = fetch or _default_fetch
    try:
        data = do_fetch(
            PHOTON_URL,
            {"q": query, "lang": "it", "limit": str(limit + 4), "lat": "42.5", "lon": "12.5"},
            timeout,
        )
    except Exception as exc:
        raise GeoError(f"Photon non raggiungibile: {exc}") from exc

    out: list[AddressSuggestion] = []
    seen: set[str] = set()
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        if props.get("countrycode") != "IT":
            continue
        desc = _photon_description(props)
        if not desc or desc in seen:
            continue
        seen.add(desc)
        out.append(
            AddressSuggestion(
                description=desc,
                municipality=props.get("city") or props.get("county"),
                source="photon",
            )
        )
        if len(out) >= limit:
            break
    return out


def _use_online(fetch: Fetcher | None) -> bool:
    """Se usare provider online: sempre con fetch iniettato (test), altrimenti salvo
    quando ``BRICKVALUE_OFFLINE`` e' impostata (per i test deterministici)."""
    return fetch is not None or not os.environ.get("BRICKVALUE_OFFLINE")


def suggest_addresses(
    query: str,
    *,
    api_key: str | None = None,
    fetch: Fetcher | None = None,
    limit: int = 5,
) -> SuggestResult:
    """Autocompletamento indirizzo: Google Places (se chiave) -> Photon (gratuito,
    livello via) -> comuni del dataset (offline). Non solleva mai."""
    limit = max(1, min(10, limit))

    # 1. Google Places (massima precisione, richiede chiave)
    if api_key or is_google_enabled():
        try:
            preds = autocomplete(query, api_key=api_key, fetch=fetch, limit=limit)
            if preds:
                return SuggestResult(query=query, source="google", suggestions=preds)
        except GeoError:
            pass

    # 2. Photon (gratuito, livello via/civico) quando c'e' rete
    if _use_online(fetch):
        try:
            preds = photon_autocomplete(query, fetch=fetch, limit=limit)
            if preds:
                return SuggestResult(query=query, source="photon", suggestions=preds)
        except GeoError:
            pass

    # 3. Dataset dei comuni (sempre disponibile, offline)
    suggestions = [
        AddressSuggestion(
            description=f"{place.name} ({place.prov})", municipality=place.name, source="dataset"
        )
        for place in suggest_cities(query, limit)
    ]
    return SuggestResult(
        query=query,
        source="dataset" if suggestions else "nessuna",
        suggestions=suggestions,
    )
