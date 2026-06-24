"""Inferenza dei parametri di stima a partire dalla localizzazione.

Da un :class:`GeoLocation` deduce:

* ``base_unit_value`` (€/m²) = prezzo medio della citta'/regione corretto da un
  moltiplicatore di centralita' (distanza dal centro citta', se note le coordinate);
* ``cap_rate`` per fascia di prezzo;
* ``construction_cost_multiplier`` su base regionale.
"""

from __future__ import annotations

from brickvalue.data.market_reference import (
    NATIONAL_DEFAULT_PRICE,
    centrality_multiplier,
    construction_multiplier,
    haversine_km,
    lookup_place,
    region_price,
    resolve_region,
)
from brickvalue.domain.enums import PropertyType
from brickvalue.domain.geo import GeoLocation, InferredParameters
from brickvalue.utils import round_money


def _cap_rate_for_price(price: float) -> float:
    """Saggio di capitalizzazione residenziale indicativo per fascia di prezzo."""
    if price >= 3800:
        return 0.030
    if price >= 2800:
        return 0.033
    if price >= 2000:
        return 0.037
    if price >= 1400:
        return 0.042
    return 0.047


def infer_parameters(
    location: GeoLocation,
    property_type: PropertyType | None = None,
) -> InferredParameters:
    """Deduce i parametri di stima dalla localizzazione."""
    notes: list[str] = []

    # 1) Prezzo base di zona e baricentro comune
    city_name: str | None = None
    region: str | None = resolve_region(location.region)
    centroid: tuple[float, float] | None = None

    place = lookup_place(location.municipality, location.province)
    if place is not None:
        city_name = place.name
        region = place.region
        if place.lat is not None and place.lon is not None:
            centroid = (place.lat, place.lon)
        if place.eur_sqm is not None:
            base_price = place.eur_sqm
            notes.append(f"Valore di zona dal riferimento cittadino di {city_name}.")
        else:
            base_price = region_price(place.region) or NATIONAL_DEFAULT_PRICE
            notes.append(f"Comune {city_name}: usata la media regionale ({region}).")
        confidence = "alta" if location.source == "google" else "media"
    else:
        rp = region_price(location.region)
        if rp is not None:
            base_price = rp
            notes.append(f"Comune non riconosciuto: usata la media regionale ({region}).")
            confidence = "media" if location.source == "google" else "bassa"
        else:
            base_price = NATIONAL_DEFAULT_PRICE
            notes.append("Localita' non riconosciuta: usato il valore nazionale di default.")
            confidence = "bassa"

    # 2) Centralita' dalle coordinate (se disponibili e baricentro noto)
    centrality: float | None = None
    distance_km: float | None = None
    if location.lat is not None and location.lng is not None and centroid is not None:
        distance_km = round(haversine_km(location.lat, location.lng, centroid[0], centroid[1]), 2)
        centrality = centrality_multiplier(distance_km)
        notes.append(
            f"Centralita' da distanza dal centro ({distance_km} km): ×{centrality:.2f}."
        )
    elif location.lat is not None and location.lng is None:  # pragma: no cover - difensivo
        pass

    base_unit_value = round_money(base_price * (centrality or 1.0))

    # 3) Saggio e costo di costruzione
    cap_rate = _cap_rate_for_price(base_price)
    cost_mult = construction_multiplier(region)
    if abs(cost_mult - 1.0) > 1e-9:
        notes.append(f"Costo di costruzione regionale ({region}): ×{cost_mult:.2f}.")

    if property_type is not None and not property_type.is_residential:
        notes.append(
            "Il valore di zona e' stimato sul residenziale: per immobili non "
            "residenziali verificare con dati specifici."
        )

    return InferredParameters(
        base_unit_value=base_unit_value,
        cap_rate=cap_rate,
        construction_cost_multiplier=cost_mult,
        centrality_multiplier=centrality,
        distance_to_center_km=distance_km,
        city=city_name or location.municipality,
        region=region,
        confidence=confidence,
        notes=notes,
    )
