"""Dati di riferimento per la stima (coefficienti e parametri di default).

I valori sono indicativi e basati sulla prassi estimativa italiana. Sono pensati
come *fallback* quando l'utente non fornisce dati puntuali: ogni parametro puo'
essere sovrascritto in input.
"""

from __future__ import annotations

from brickvalue.data.reference import (
    CONSERVATION_MERIT,
    DEFAULT_CAP_RATE,
    DEFAULT_CONSTRUCTION_COST,
    ENERGY_MERIT,
    HEIDECKE_COEFFICIENTS,
    SURFACE_COEFFICIENTS,
    USEFUL_LIFE_YEARS,
    cap_rate_for,
    construction_cost_for,
    heidecke_coefficient,
    surface_coefficient,
    useful_life_for,
)

__all__ = [
    "CONSERVATION_MERIT",
    "DEFAULT_CAP_RATE",
    "DEFAULT_CONSTRUCTION_COST",
    "ENERGY_MERIT",
    "HEIDECKE_COEFFICIENTS",
    "SURFACE_COEFFICIENTS",
    "USEFUL_LIFE_YEARS",
    "cap_rate_for",
    "construction_cost_for",
    "heidecke_coefficient",
    "surface_coefficient",
    "useful_life_for",
]
