"""Enumerazioni di dominio.

I valori delle enum usano la terminologia tecnica italiana dell'estimo, in modo
da essere autoesplicativi nelle richieste API e nei report.
"""

from __future__ import annotations

from enum import Enum


class PropertyType(str, Enum):
    """Tipologia dell'immobile da valutare."""

    APARTMENT = "appartamento"
    VILLA = "villa"
    TOWNHOUSE = "villetta_a_schiera"
    PENTHOUSE = "attico"
    STUDIO = "monolocale"
    OFFICE = "ufficio"
    SHOP = "negozio"
    WAREHOUSE = "magazzino"
    INDUSTRIAL = "capannone_industriale"
    HOTEL = "struttura_ricettiva"
    GARAGE = "box_garage"
    PARKING = "posto_auto"
    CELLAR = "cantina"
    BUILDABLE_LAND = "terreno_edificabile"
    AGRICULTURAL_LAND = "terreno_agricolo"
    BUILDING = "fabbricato_intero"

    @property
    def is_land(self) -> bool:
        return self in {PropertyType.BUILDABLE_LAND, PropertyType.AGRICULTURAL_LAND}

    @property
    def is_residential(self) -> bool:
        return self in {
            PropertyType.APARTMENT,
            PropertyType.VILLA,
            PropertyType.TOWNHOUSE,
            PropertyType.PENTHOUSE,
            PropertyType.STUDIO,
        }

    @property
    def is_commercial(self) -> bool:
        return self in {
            PropertyType.OFFICE,
            PropertyType.SHOP,
            PropertyType.WAREHOUSE,
            PropertyType.INDUSTRIAL,
            PropertyType.HOTEL,
        }


class StructureType(str, Enum):
    """Tipologia strutturale (rileva per vita utile e costo di ricostruzione)."""

    MASONRY = "muratura"
    REINFORCED_CONCRETE = "cemento_armato"
    STEEL = "acciaio"
    WOOD = "legno"
    MIXED = "mista"
    PREFABRICATED = "prefabbricato"


class ConservationState(str, Enum):
    """Stato di conservazione/manutenzione (coefficiente di Heidecke)."""

    NEW = "nuovo"
    EXCELLENT = "ottimo"
    GOOD = "buono"
    NORMAL = "normale"
    MEDIOCRE = "mediocre"
    POOR = "scadente"
    TO_RENOVATE = "da_ristrutturare"
    UNINHABITABLE = "inagibile"


class EnergyClass(str, Enum):
    """Classe energetica (APE)."""

    A4 = "A4"
    A3 = "A3"
    A2 = "A2"
    A1 = "A1"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"


class ValuationPurpose(str, Enum):
    """Finalità della stima: determina la riconciliazione e il valore di sintesi."""

    MARKET = "commerciale"
    BANKING = "bancario"
    INSURANCE = "assicurativo"
    TECHNICAL = "tecnico"
    LEGAL = "legale"


class ValuationMethod(str, Enum):
    """Metodo di stima."""

    MARKET_COMPARISON = "confronto_di_mercato"
    COST = "costo_di_ricostruzione"
    INCOME = "capitalizzazione_reddito"


class SurfaceComponentType(str, Enum):
    """Componente di superficie con il relativo coefficiente di ragguaglio."""

    MAIN = "superficie_principale"
    COVERED_BALCONY = "balcone_coperto"
    UNCOVERED_BALCONY = "balcone_scoperto"
    TERRACE = "terrazzo"
    VERANDA = "veranda"
    GARDEN_APARTMENT = "giardino_appartamento"
    GARDEN_VILLA = "giardino_villa"
    CELLAR_ATTIC = "cantina_soffitta"
    TAVERNA = "taverna"
    GARAGE = "box_garage"
    PARKING_COVERED = "posto_auto_coperto"
    PARKING_UNCOVERED = "posto_auto_scoperto"
    LOW_HEIGHT = "locale_altezza_ridotta"
    PORCH = "portico"
