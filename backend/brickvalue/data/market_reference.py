"""Dataset di riferimento dei valori immobiliari per localita'.

Combina:

* l'elenco completo dei comuni italiani (``comuni.json``, ~7.900 voci con
  provincia, regione e centro rappresentativo) per autocompletamento e
  riconoscimento dell'indirizzo;
* valori €/m² *curati* per le principali citta' (piu' accurati e con baricentro
  preciso), sovrapposti ai comuni corrispondenti;
* medie regionali e moltiplicatori del costo di costruzione.

I valori monetari sono indicativi (ordine di grandezza, residenziale) e vanno
verificati con quotazioni reali (es. OMI). La precisione aumenta con la
geocodifica Google (coordinate dell'indirizzo -> distanza dal centro comune).
"""

from __future__ import annotations

import json
import math
import unicodedata
from dataclasses import dataclass
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Normalizzazione e geometria
# ---------------------------------------------------------------------------
def normalize(text: str) -> str:
    """Normalizza un testo per il confronto (minuscolo, senza accenti/punteggiatura)."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    cleaned = "".join(c if c.isalnum() else " " for c in no_accents.lower())
    return " ".join(cleaned.split())


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distanza in km tra due coordinate (formula dell'emisenoverso)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def centrality_multiplier(distance_km: float) -> float:
    """Moltiplicatore di centralita' in funzione della distanza dal centro comune."""
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


# ---------------------------------------------------------------------------
# Prezzi curati delle principali citta' (€/m², baricentro preciso)
# I nomi sono quelli ufficiali ISTAT (per la sovrapposizione ai comuni).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CityRef:
    province: str
    region: str
    lat: float
    lng: float
    eur_sqm: float


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
    "Bolzano/Bozen": CityRef("BZ", "Trentino-Alto Adige", 46.4983, 11.3548, 4700),
    "Trento": CityRef("TN", "Trentino-Alto Adige", 46.0700, 11.1190, 3000),
    "Trieste": CityRef("TS", "Friuli-Venezia Giulia", 45.6495, 13.7768, 2100),
    "Udine": CityRef("UD", "Friuli-Venezia Giulia", 46.0711, 13.2346, 1600),
    "Parma": CityRef("PR", "Emilia-Romagna", 44.8015, 10.3279, 2400),
    "Modena": CityRef("MO", "Emilia-Romagna", 44.6471, 10.9252, 2400),
    "Reggio nell'Emilia": CityRef("RE", "Emilia-Romagna", 44.6983, 10.6312, 1900),
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
    "Reggio di Calabria": CityRef("RC", "Calabria", 38.1147, 15.6500, 1300),
    "Catanzaro": CityRef("CZ", "Calabria", 38.9098, 16.5877, 1200),
    "Novara": CityRef("NO", "Piemonte", 45.4459, 8.6216, 1500),
    "Aosta": CityRef("AO", "Valle d'Aosta", 45.7372, 7.3206, 2200),
    "La Spezia": CityRef("SP", "Liguria", 44.1025, 9.8241, 2500),
}

# Alias comuni (forme correnti) -> nome ufficiale, per il riconoscimento testuale.
COMMON_ALIASES: dict[str, str] = {
    "reggio emilia": "Reggio nell'Emilia",
    "reggio calabria": "Reggio di Calabria",
    "bolzano": "Bolzano/Bozen",
}


# ---------------------------------------------------------------------------
# Medie regionali e moltiplicatori
# ---------------------------------------------------------------------------
REGION_PRICES: dict[str, float] = {
    "Lombardia": 2200, "Lazio": 2400, "Toscana": 2600, "Emilia-Romagna": 2300,
    "Veneto": 2000, "Campania": 1900, "Piemonte": 1600, "Liguria": 2200,
    "Sicilia": 1300, "Puglia": 1400, "Sardegna": 1700, "Trentino-Alto Adige": 3400,
    "Friuli-Venezia Giulia": 1600, "Marche": 1700, "Abruzzo": 1400, "Calabria": 1100,
    "Umbria": 1500, "Basilicata": 1200, "Molise": 1100, "Valle d'Aosta": 2200,
}

NATIONAL_DEFAULT_PRICE = 1700.0

REGION_CONSTRUCTION_MULT: dict[str, float] = {
    "Lombardia": 1.08, "Trentino-Alto Adige": 1.10, "Veneto": 1.03, "Emilia-Romagna": 1.04,
    "Liguria": 1.05, "Piemonte": 1.02, "Friuli-Venezia Giulia": 1.00, "Valle d'Aosta": 1.06,
    "Lazio": 1.03, "Toscana": 1.03, "Marche": 0.98, "Umbria": 0.97, "Abruzzo": 0.95,
    "Campania": 0.95, "Puglia": 0.93, "Basilicata": 0.92, "Calabria": 0.90, "Sicilia": 0.92,
    "Sardegna": 0.96, "Molise": 0.92,
}

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
    canonical = resolve_region(region)
    return REGION_PRICES.get(canonical) if canonical else None


def construction_multiplier(region: str | None) -> float:
    canonical = resolve_region(region)
    if not canonical:
        return 1.0
    return REGION_CONSTRUCTION_MULT.get(canonical, 1.0)


# ---------------------------------------------------------------------------
# Indice unificato dei comuni
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PlaceRef:
    name: str
    prov: str
    region: str
    lat: float | None
    lon: float | None
    eur_sqm: float | None
    pop: int = 0


def _load_places() -> tuple[dict[str, PlaceRef], dict[str, str], list[tuple[str, PlaceRef]]]:
    """Carica i comuni e sovrappone i prezzi curati. Restituisce:

    * by_norm: nome normalizzato -> PlaceRef
    * alias_to_norm: alias normalizzato -> nome normalizzato canonico
    * text_index: lista (norm, PlaceRef) ordinata per lunghezza decrescente
    """
    rows = json.loads((_DATA_DIR / "comuni.json").read_text(encoding="utf-8"))
    by_norm: dict[str, PlaceRef] = {}
    for name, prov, region, lat, lon, pop in rows:
        norm = normalize(name)
        keep = by_norm.get(norm)
        # tra gli omonimi tiene quello piu' popoloso
        if keep is None or pop > keep.pop:
            by_norm[norm] = PlaceRef(name, prov, region, lat, lon, None, pop)

    # Sovrappone i prezzi curati (nomi ufficiali -> match diretto).
    for cname, ref in CITY_PRICES.items():
        norm = normalize(cname)
        existing = by_norm.get(norm)
        official = existing.name if existing else cname
        pop = existing.pop if existing else 0
        by_norm[norm] = PlaceRef(official, ref.province, ref.region, ref.lat, ref.lng, ref.eur_sqm, pop)

    alias_to_norm: dict[str, str] = {}
    text_index: list[tuple[str, PlaceRef]] = []
    for norm, place in by_norm.items():
        text_index.append((norm, place))
        # alias bilingui: "Bolzano/Bozen" -> "bolzano", "bozen"
        if "/" in place.name:
            for seg in place.name.split("/"):
                seg_norm = normalize(seg)
                if seg_norm and seg_norm != norm:
                    alias_to_norm[seg_norm] = norm
                    text_index.append((seg_norm, place))
    for alias, official in COMMON_ALIASES.items():
        onorm = normalize(official)
        if onorm in by_norm:
            alias_to_norm[normalize(alias)] = onorm
            text_index.append((normalize(alias), by_norm[onorm]))

    text_index.sort(key=lambda t: len(t[0]), reverse=True)
    return by_norm, alias_to_norm, text_index


_PLACES_BY_NORM, _ALIAS_TO_NORM, _TEXT_INDEX = _load_places()
_SUGGEST_INDEX: list[tuple[str, PlaceRef]] = sorted(
    ((norm, place) for norm, place in _PLACES_BY_NORM.items()), key=lambda t: t[1].name
)


def lookup_place(name: str | None, province: str | None = None) -> PlaceRef | None:
    """Risolve un comune per nome (gestendo alias bilingui e forme correnti)."""
    if not name:
        return None
    norm = normalize(name)
    norm = _ALIAS_TO_NORM.get(norm, norm)
    return _PLACES_BY_NORM.get(norm)


def find_place_in_text(text: str) -> PlaceRef | None:
    """Trova il comune piu' lungo presente come sequenza di parole nell'indirizzo."""
    norm_text = f" {normalize(text)} "
    for norm, place in _TEXT_INDEX:
        if len(norm) >= 4 and f" {norm} " in norm_text:
            return place
    return None


def find_city_in_text(text: str) -> str | None:
    """Nome del comune riconosciuto nell'indirizzo (None se nessuno)."""
    place = find_place_in_text(text)
    return place.name if place else None


def suggest_cities(query: str, limit: int = 5) -> list[PlaceRef]:
    """Suggerisce comuni in base alla digitazione.

    Match per *prefisso di parola* (niente match a meta' parola) e ordinamento
    per rilevanza: prima il prefisso del nome intero, poi i comuni piu' popolosi.
    Per gli indirizzi (es. "via roma mil") considera l'ultima parola = comune.
    """
    nq = normalize(query)
    if len(nq) < 2:
        return []
    tokens = nq.split()
    last = tokens[-1]
    use_last = len(last) >= 2

    scored: list[tuple[int, int, str, PlaceRef]] = []
    for norm, place in _SUGGEST_INDEX:
        words = norm.split()
        if norm.startswith(nq):
            tier = 0
        elif all(any(w.startswith(tok) for w in words) for tok in tokens):
            tier = 1
        elif use_last and words[0].startswith(last):
            tier = 2
        elif use_last and any(w.startswith(last) for w in words):
            tier = 3
        else:
            continue
        scored.append((tier, -place.pop, place.name, place))

    scored.sort(key=lambda t: (t[0], t[1], t[2]))
    result: list[PlaceRef] = []
    seen: set[str] = set()
    for _, _, name, place in scored:
        if name in seen:
            continue
        seen.add(name)
        result.append(place)
        if len(result) >= limit:
            break
    return result
