"""Geolocalizzazione (Google Maps) e risoluzione degli indirizzi."""

from __future__ import annotations

from brickvalue.geo.client import (
    GeoError,
    autocomplete,
    geocode,
    is_google_enabled,
    photon_autocomplete,
    resolve_location,
    suggest_addresses,
)

__all__ = [
    "GeoError",
    "autocomplete",
    "geocode",
    "is_google_enabled",
    "photon_autocomplete",
    "resolve_location",
    "suggest_addresses",
]
