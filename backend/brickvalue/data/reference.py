"""Tabelle e parametri di riferimento.

NOTA METODOLOGICA
-----------------
I valori monetari (costi di costruzione) e i saggi sono *indicativi* e servono
come default ragionevoli in assenza di dati puntuali (es. quotazioni OMI di
zona o computo metrico). In una perizia reale vanno sostituiti con dati di
mercato verificati. La struttura del codice consente di farlo via input senza
modificare queste tabelle.
"""

from __future__ import annotations

from brickvalue.domain.enums import (
    ConservationState,
    EnergyClass,
    PropertyType,
    StructureType,
    SurfaceComponentType,
)

# ---------------------------------------------------------------------------
# Coefficienti di ragguaglio della superficie commerciale
# ---------------------------------------------------------------------------
# Frazione con cui ciascuna superficie concorre alla superficie commerciale,
# secondo la prassi estimativa (cfr. norme UNI/standard di mercato).
SURFACE_COEFFICIENTS: dict[SurfaceComponentType, float] = {
    SurfaceComponentType.MAIN: 1.00,
    SurfaceComponentType.COVERED_BALCONY: 0.35,
    SurfaceComponentType.UNCOVERED_BALCONY: 0.30,
    SurfaceComponentType.TERRACE: 0.30,
    SurfaceComponentType.VERANDA: 0.60,
    SurfaceComponentType.GARDEN_APARTMENT: 0.15,
    SurfaceComponentType.GARDEN_VILLA: 0.10,
    SurfaceComponentType.CELLAR_ATTIC: 0.25,
    SurfaceComponentType.TAVERNA: 0.50,
    SurfaceComponentType.GARAGE: 0.50,
    SurfaceComponentType.PARKING_COVERED: 0.30,
    SurfaceComponentType.PARKING_UNCOVERED: 0.20,
    SurfaceComponentType.LOW_HEIGHT: 0.30,
    SurfaceComponentType.PORCH: 0.35,
}


def surface_coefficient(component: SurfaceComponentType) -> float:
    """Coefficiente di ragguaglio di default per una componente di superficie."""
    return SURFACE_COEFFICIENTS[component]


# ---------------------------------------------------------------------------
# Coefficienti di merito per stato di conservazione (confronto di mercato)
# ---------------------------------------------------------------------------
# Moltiplicatori del valore unitario rispetto allo stato "normale" (= 1.00).
CONSERVATION_MERIT: dict[ConservationState, float] = {
    ConservationState.NEW: 1.15,
    ConservationState.EXCELLENT: 1.10,
    ConservationState.GOOD: 1.05,
    ConservationState.NORMAL: 1.00,
    ConservationState.MEDIOCRE: 0.90,
    ConservationState.POOR: 0.80,
    ConservationState.TO_RENOVATE: 0.70,
    ConservationState.UNINHABITABLE: 0.55,
}


# ---------------------------------------------------------------------------
# Coefficienti di merito per classe energetica
# ---------------------------------------------------------------------------
ENERGY_MERIT: dict[EnergyClass, float] = {
    EnergyClass.A4: 1.10,
    EnergyClass.A3: 1.08,
    EnergyClass.A2: 1.06,
    EnergyClass.A1: 1.04,
    EnergyClass.B: 1.02,
    EnergyClass.C: 1.00,
    EnergyClass.D: 0.98,
    EnergyClass.E: 0.96,
    EnergyClass.F: 0.93,
    EnergyClass.G: 0.90,
}


# ---------------------------------------------------------------------------
# Coefficienti di Heidecke per stato di manutenzione (deprezzamento)
# ---------------------------------------------------------------------------
# Tabella canonica del metodo di Ross-Heidecke: quota di deprezzamento dovuta
# allo stato di conservazione, da combinare con il deprezzamento da vetusta'.
HEIDECKE_COEFFICIENTS: dict[ConservationState, float] = {
    ConservationState.NEW: 0.0000,
    ConservationState.EXCELLENT: 0.0032,
    ConservationState.GOOD: 0.0252,
    ConservationState.NORMAL: 0.0809,
    ConservationState.MEDIOCRE: 0.1810,
    ConservationState.POOR: 0.3320,
    ConservationState.TO_RENOVATE: 0.5260,
    ConservationState.UNINHABITABLE: 0.7520,
}


def heidecke_coefficient(state: ConservationState) -> float:
    """Coefficiente di Heidecke per lo stato di conservazione indicato."""
    return HEIDECKE_COEFFICIENTS[state]


# ---------------------------------------------------------------------------
# Costo di ricostruzione a nuovo (€/m² di superficie lorda)
# ---------------------------------------------------------------------------
# Valori indicativi del solo costo di costruzione "a misura" (esclusi oneri,
# spese tecniche, utile e suolo, che sono aggiunti dal motore di costo).
DEFAULT_CONSTRUCTION_COST: dict[PropertyType, float] = {
    PropertyType.APARTMENT: 1350.0,
    PropertyType.VILLA: 1700.0,
    PropertyType.TOWNHOUSE: 1500.0,
    PropertyType.PENTHOUSE: 1600.0,
    PropertyType.STUDIO: 1300.0,
    PropertyType.OFFICE: 1250.0,
    PropertyType.SHOP: 1150.0,
    PropertyType.WAREHOUSE: 700.0,
    PropertyType.INDUSTRIAL: 650.0,
    PropertyType.HOTEL: 1600.0,
    PropertyType.GARAGE: 550.0,
    PropertyType.PARKING: 250.0,
    PropertyType.CELLAR: 450.0,
    PropertyType.BUILDING: 1300.0,
}


def construction_cost_for(property_type: PropertyType) -> float:
    """Costo di costruzione a nuovo di riferimento (€/m²) per tipologia.

    Per i terreni non e' definito un costo di costruzione.
    """
    if property_type.is_land:
        raise ValueError("Il costo di costruzione non si applica ai terreni")
    return DEFAULT_CONSTRUCTION_COST.get(property_type, 1300.0)


# ---------------------------------------------------------------------------
# Vita utile (anni) per il deprezzamento, per tipologia strutturale
# ---------------------------------------------------------------------------
USEFUL_LIFE_YEARS: dict[StructureType, int] = {
    StructureType.MASONRY: 100,
    StructureType.REINFORCED_CONCRETE: 80,
    StructureType.STEEL: 70,
    StructureType.WOOD: 60,
    StructureType.MIXED: 80,
    StructureType.PREFABRICATED: 50,
}


def useful_life_for(structure: StructureType) -> int:
    """Vita utile economica di riferimento (anni) per la struttura indicata."""
    return USEFUL_LIFE_YEARS.get(structure, 80)


# ---------------------------------------------------------------------------
# Saggio di capitalizzazione (metodo reddituale)
# ---------------------------------------------------------------------------
DEFAULT_CAP_RATE: dict[PropertyType, float] = {
    PropertyType.APARTMENT: 0.035,
    PropertyType.VILLA: 0.030,
    PropertyType.TOWNHOUSE: 0.033,
    PropertyType.PENTHOUSE: 0.033,
    PropertyType.STUDIO: 0.045,
    PropertyType.OFFICE: 0.055,
    PropertyType.SHOP: 0.065,
    PropertyType.WAREHOUSE: 0.075,
    PropertyType.INDUSTRIAL: 0.080,
    PropertyType.HOTEL: 0.070,
    PropertyType.GARAGE: 0.050,
    PropertyType.PARKING: 0.055,
    PropertyType.BUILDING: 0.045,
}


def cap_rate_for(property_type: PropertyType) -> float:
    """Saggio di capitalizzazione di riferimento per tipologia."""
    return DEFAULT_CAP_RATE.get(property_type, 0.045)
