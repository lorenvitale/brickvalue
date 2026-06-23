"""Client di geocodifica.

Usa l'API Google Maps Geocoding quando e' configurata la variabile d'ambiente
``GOOGLE_MAPS_API_KEY``; in assenza di chiave (o in caso di errore) ricade su un
riconoscimento testuale del comune basato sul dataset di riferimento.

Il client e' iniettabile (parametro ``fetch``) per consentire i test senza rete.
"""

from __future__ import annotations

import os
from typing import Callable

from brickvalue.data.market_reference import CITY_PRICES, find_city_in_text
from brickvalue.domain.geo import GeoLocation

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

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

    city = find_city_in_text(address or "")
    if city:
        ref = CITY_PRICES[city]
        return GeoLocation(
            query=address,
            source="fallback_testuale",
            municipality=city,
            province=ref.province,
            region=ref.region,
        )
    return GeoLocation(query=address, source="sconosciuto")
