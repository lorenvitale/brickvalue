"""Dataset di riferimento dei valori immobiliari per localita' (indicativo).

Serve a *dedurre* i parametri di stima dall'indirizzo quando l'utente non li
fornisce: valore unitario di zona (€/m²), saggio di capitalizzazione e
moltiplicatore regionale del costo di costruzione.

NOTA: i valori sono indicativi (ordine di grandezza, mercato residenziale) e
vanno verificati con quotazioni reali (es. OMI). La precisione aumenta quando e'
disponibile la geocodifica Google (coordinate -> distanza dal centro citta').
"""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class CityRef:
    """Riferimento per una citta': provincia, regione, baricentro, €/m² medio."""

    province: str
    region: str
    lat: float
    lng: float
    eur_sqm: float


# Valore €/m² = media cittadina indicativa del residenziale (2024, ordine di grandezza).
CITY_PRICES: dict[str, CityRef] = {
    "Milano": CityRef("MI", "Lombardia", 45.4642, 9.1900, 4900),
    "Roma": CityRef("RM", "Lazio", 41.9028, 12.4964, 3200),
    "Napoli": CityRef("NA", "Campania", 40.8518, 14.2681, 2800),
    "Torino": CityRef("TO", "Piemonte", 45.0703, 7.6869, 1900),
    "Firenze": CityRef("FI", "Toscana", 43.7696, 11.2558, 4000),
    "Bologna": CityRef("BO", "Emilia-Romagna", 44.4949, 11.3426, 3300),
    "Venezia": CityRef("VE", "Veneto", 45.4408, 12.3155, 4600),
    "Genova": CityRef("GE", "Liguria", 44.4056, 8.9463, 1700),
    "Verona": CityRef("VR", "Veneto", 45.4384, 10.9916, 2600),
    "Padova": CityRef("PD", "Veneto", 45.4064, 11.8768, 2500),
    "Vicenza": CityRef("VI", "Veneto", 45.5455, 11.5354, 1900),
    "Treviso": CityRef("TV", "Veneto", 45.6669, 12.2430, 2300),
    "Bergamo": CityRef("BG", "Lombardia", 45.6983, 9.6773, 2400),
    "Brescia": CityRef("BS", "Lombardia", 45.5416, 10.2118, 2000),
    "Como": CityRef("CO", "Lombardia", 45.8081, 9.0852, 2900),
    "Monza": CityRef("MB", "Lombardia", 45.5845, 9.2744, 2700),
    "Pavia": CityRef("PV", "Lombardia", 45.1847, 9.1582, 2100),
    "Cremona": CityRef("CR", "Lombardia", 45.1332, 10.0226, 1600),
    "Varese": CityRef("VA", "Lombardia", 45.8206, 8.8251, 1700),
    "Bolzano": CityRef("BZ", "Trentino-Alto Adige", 46.4983, 11.3548, 4700),
    "Trento": CityRef("TN", "Trentino-Alto Adige", 46.0700, 11.1190, 3000),
    "Trieste": CityRef("TS", "Friuli-Venezia Giulia", 45.6495, 13.7768, 2100),
    "Udine": CityRef("UD", "Friuli-Venezia Giulia", 46.0711, 13.2346, 1600),
    "Parma": CityRef("PR", "Emilia-Romagna", 44.8015, 10.3279, 2400),
    "Modena": CityRef("MO", "Emilia-Romagna", 44.6471, 10.9252, 2400),
    "Reggio Emilia": CityRef("RE", "Emilia-Romagna", 44.6983, 10.6312, 1900),
    "Rimini": CityRef("RN", "Emilia-Romagna", 44.0678, 12.5695, 3000),
    "Ravenna": CityRef("RA", "Emilia-Romagna", 44.4184, 12.2035, 1900),
    "Ferrara": CityRef("FE", "Emilia-Romagna", 44.8381, 11.6198, 1700),
    "Bari": CityRef("BA", "Puglia", 41.1171, 16.8719, 2300),
    "Lecce": CityRef("LE", "Puglia", 40.3515, 18.1750, 1700),
    "Taranto": CityRef("TA", "Puglia", 40.4644, 17.2470, 1100),
    "Foggia": CityRef("FG", "Puglia", 41.4622, 15.5446, 1200),
    "Catania": CityRef("CT", "Sicilia", 37.5079, 15.0830, 1500),
    "Palermo": CityRef("PA", "Sicilia", 38.1157, 13.3615, 1400),
    "Messina": CityRef("ME", "Sicilia", 38.1938, 15.5540, 1300),
    "Cagliari": CityRef("CA", "Sardegna", 39.2238, 9.1217, 2300),
    "Sassari": CityRef("SS", "Sardegna", 40.7259, 8.5557, 1400),
    "Pisa": CityRef("PI", "Toscana", 43.7160, 10.4017, 2700),
    "Siena": CityRef("SI", "Toscana", 43.3188, 11.3308, 2900),
    "Lucca": CityRef("LU", "Toscana", 43.8430, 10.5079, 2700),
    "Perugia": CityRef("PG", "Umbria", 43.1107, 12.3908, 1700),
    "Ancona": CityRef("AN", "Marche", 43.6158, 13.5189, 1900),
    "Pescara": CityRef("PE", "Abruzzo", 42.4618, 14.2160, 1900),
    "L'Aquila": CityRef("AQ", "Abruzzo", 42.3498, 13.3995, 1500),
    "Salerno": CityRef("SA", "Campania", 40.6824, 14.7681, 2400),
    "Cosenza": CityRef("CS", "Calabria", 39.2983, 16.2536, 1200),
    "Reggio Calabria": CityRef("RC", "Calabria", 38.1147, 15.6500, 1300),
    "Catanzaro": CityRef("CZ", "Calabria", 38.9098, 16.5877, 1200),
    "Novara": CityRef("NO", "Piemonte", 45.4459, 8.6216, 1500),
    "Aosta": CityRef("AO", "Valle d'Aosta", 45.7372, 7.3206, 2200),
    "La Spezia": CityRef("SP", "Liguria", 44.1025, 9.8241, 2500),
}

# Media regionale (€/m²) usata quando la citta' non e' in tabella.
REGION_PRICES: dict[str, float] = {
    "Lombardia": 2200,
    "Lazio": 2400,
    "Toscana": 2600,
    "Emilia-Romagna": 2300,
    "Veneto": 2000,
    "Campania": 1900,
    "Piemonte": 1600,
    "Liguria": 2200,
    "Sicilia": 1300,
    "Puglia": 1400,
    "Sardegna": 1700,
    "Trentino-Alto Adige": 3400,
    "Friuli-Venezia Giulia": 1600,
    "Marche": 1700,
    "Abruzzo": 1400,
    "Calabria": 1100,
    "Umbria": 1500,
    "Basilicata": 1200,
    "Molise": 1100,
    "Valle d'Aosta": 2200,
}

NATIONAL_DEFAULT_PRICE = 1700.0

# Moltiplicatore regionale del costo di costruzione (rispetto al riferimento nazionale).
REGION_CONSTRUCTION_MULT: dict[str, float] = {
    "Lombardia": 1.08,
    "Trentino-Alto Adige": 1.10,
    "Veneto": 1.03,
    "Emilia-Romagna": 1.04,
    "Liguria": 1.05,
    "Piemonte": 1.02,
    "Friuli-Venezia Giulia": 1.00,
    "Valle d'Aosta": 1.06,
    "Lazio": 1.03,
    "Toscana": 1.03,
    "Marche": 0.98,
    "Umbria": 0.97,
    "Abruzzo": 0.95,
    "Campania": 0.95,
    "Puglia": 0.93,
    "Basilicata": 0.92,
    "Calabria": 0.90,
    "Sicilia": 0.92,
    "Sardegna": 0.96,
    "Molise": 0.92,
}


def normalize(text: str) -> str:
    """Normalizza un testo per il confronto (minuscolo, senza accenti/punteggiatura)."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    cleaned = "".join(c if c.isalnum() else " " for c in no_accents.lower())
    return " ".join(cleaned.split())


# Indice normalizzato delle citta' (piu' lunghe prima, per matchare "reggio emilia"
# prima di un'eventuale "reggio").
_CITY_INDEX: list[tuple[str, str]] = sorted(
    ((normalize(name), name) for name in CITY_PRICES),
    key=lambda t: len(t[0]),
    reverse=True,
)


def find_city_in_text(text: str) -> str | None:
    """Cerca un comune noto come sequenza di parole nell'indirizzo."""
    norm = f" {normalize(text)} "
    for norm_city, original in _CITY_INDEX:
        if f" {norm_city} " in norm:
            return original
    return None


def suggest_cities(query: str, limit: int = 5) -> list[tuple[str, CityRef]]:
    """Suggerisce comuni dal dataset in base alla digitazione (fallback senza Google).

    Ordina prima le citta' il cui nome inizia con il testo digitato, poi quelle
    che lo contengono.
    """
    nq = normalize(query)
    if not nq:
        return []
    last = nq.split()[-1]
    prefix: list[tuple[str, CityRef]] = []
    contains: list[tuple[str, CityRef]] = []
    for name, ref in CITY_PRICES.items():
        nc = normalize(name)
        if nc.startswith(nq) or nc.startswith(last):
            prefix.append((name, ref))
        elif nq in nc or (len(last) >= 3 and last in nc):
            contains.append((name, ref))
    ordered = prefix + contains
    return ordered[:limit]


def lookup_city(name: str | None) -> tuple[str, CityRef] | None:
    """Restituisce (nome, CityRef) se il comune e' in tabella."""
    if not name:
        return None
    target = normalize(name)
    for norm_city, original in _CITY_INDEX:
        if norm_city == target:
            return original, CITY_PRICES[original]
    return None


_REGION_INDEX: dict[str, str] = {normalize(name): name for name in REGION_PRICES}


def resolve_region(name: str | None) -> str | None:
    """Mappa una stringa regione (anche bilingue Google) sulla chiave canonica."""
    if not name:
        return None
    norm = normalize(name)
    if norm in _REGION_INDEX:
        return _REGION_INDEX[norm]
    for norm_region, original in _REGION_INDEX.items():
        if norm.startswith(norm_region) or norm_region in norm:
            return original
    return None


def region_price(region: str | None) -> float | None:
    """Prezzo medio regionale, se la regione e' nota."""
    canonical = resolve_region(region)
    return REGION_PRICES.get(canonical) if canonical else None


def construction_multiplier(region: str | None) -> float:
    """Moltiplicatore regionale del costo di costruzione (1.0 se regione ignota)."""
    canonical = resolve_region(region)
    if not canonical:
        return 1.0
    return REGION_CONSTRUCTION_MULT.get(canonical, 1.0)


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distanza in km tra due coordinate (formula dell'emisenoverso)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def centrality_multiplier(distance_km: float) -> float:
    """Moltiplicatore di centralita' in funzione della distanza dal centro citta'."""
    if distance_km < 1.0:
        return 1.30
    if distance_km < 2.0:
        return 1.15
    if distance_km < 4.0:
        return 1.05
    if distance_km < 7.0:
        return 1.00
    if distance_km < 12.0:
        return 0.90
    return 0.82
