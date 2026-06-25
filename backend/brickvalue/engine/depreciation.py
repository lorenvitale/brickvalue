"""Calcolo del deprezzamento con il metodo di Ross-Heidecke.

Il deprezzamento combina due effetti:

* **Ross** — deperimento fisiologico per vetusta', funzione dell'eta' rapportata
  alla vita utile (curva intermedia tra lineare e parabolica):

      Dr = 1/2 · (a + a²)        con a = eta' / vita_utile,  a ∈ [0, 1]

* **Heidecke** — deperimento aggiuntivo per stato di manutenzione, dato da un
  coefficiente C tabellato in funzione dello stato di conservazione.

Il deprezzamento totale e':

      D = Dr + C · (1 − Dr)

da cui il valore residuo:

      residuo = (1 − Dr) · (1 − C)
"""

from __future__ import annotations

from brickvalue.data.reference import heidecke_coefficient
from brickvalue.domain.enums import ConservationState
from brickvalue.domain.results import DepreciationResult
from brickvalue.utils import clamp, safe_div


def ross_coefficient(age_years: float, useful_life_years: float) -> float:
    """Frazione di deprezzamento di Ross (vetusta'), nell'intervallo [0, 1]."""
    if useful_life_years <= 0:
        raise ValueError("La vita utile deve essere positiva")
    a = clamp(safe_div(age_years, useful_life_years), 0.0, 1.0)
    return 0.5 * (a + a * a)


def compute_depreciation(
    age_years: int,
    useful_life_years: int,
    conservation: ConservationState,
) -> DepreciationResult:
    """Calcola il deprezzamento di Ross-Heidecke."""
    if age_years < 0:
        raise ValueError("L'eta' non puo' essere negativa")
    if useful_life_years <= 0:
        raise ValueError("La vita utile deve essere positiva")

    a = clamp(age_years / useful_life_years, 0.0, 1.0)
    d_ross = 0.5 * (a + a * a)
    c_heid = heidecke_coefficient(conservation)
    total = clamp(d_ross + c_heid * (1.0 - d_ross), 0.0, 1.0)
    residual = clamp(1.0 - total, 0.0, 1.0)

    notes: list[str] = []
    if age_years >= useful_life_years:
        notes.append(
            "L'eta' raggiunge o supera la vita utile: deprezzamento da vetusta' al massimo."
        )

    return DepreciationResult(
        method="ross-heidecke",
        age_years=age_years,
        useful_life_years=useful_life_years,
        age_ratio=round(a, 4),
        ross_coefficient=round(d_ross, 4),
        heidecke_coefficient=round(c_heid, 4),
        total_depreciation=round(total, 4),
        residual_ratio=round(residual, 4),
        notes=notes,
    )
