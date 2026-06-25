"""Riconciliazione dei valori ottenuti dai diversi metodi di stima.

La sintesi e' una media ponderata dei valori dei metodi disponibili; i pesi
dipendono dalla finalita' della stima. I pesi vengono normalizzati sui soli
metodi effettivamente calcolati.
"""

from __future__ import annotations

from brickvalue.domain.enums import ValuationMethod, ValuationPurpose
from brickvalue.domain.results import ReconciliationResult
from brickvalue.utils import round_money

# Pesi di base per metodo, in funzione della finalita'.
DEFAULT_WEIGHTS: dict[ValuationPurpose, dict[ValuationMethod, float]] = {
    ValuationPurpose.MARKET: {
        ValuationMethod.MARKET_COMPARISON: 0.70,
        ValuationMethod.INCOME: 0.20,
        ValuationMethod.COST: 0.10,
    },
    ValuationPurpose.BANKING: {
        ValuationMethod.MARKET_COMPARISON: 0.60,
        ValuationMethod.COST: 0.25,
        ValuationMethod.INCOME: 0.15,
    },
    ValuationPurpose.INSURANCE: {
        ValuationMethod.COST: 0.80,
        ValuationMethod.MARKET_COMPARISON: 0.20,
    },
    ValuationPurpose.TECHNICAL: {
        ValuationMethod.COST: 0.60,
        ValuationMethod.MARKET_COMPARISON: 0.30,
        ValuationMethod.INCOME: 0.10,
    },
    ValuationPurpose.LEGAL: {
        ValuationMethod.MARKET_COMPARISON: 0.50,
        ValuationMethod.COST: 0.30,
        ValuationMethod.INCOME: 0.20,
    },
}


def reconcile(
    purpose: ValuationPurpose,
    method_values: dict[ValuationMethod, float],
) -> ReconciliationResult:
    """Calcola il valore di sintesi come media ponderata.

    ``method_values`` mappa ciascun metodo al relativo valore di mercato. Per il
    metodo del costo va passato il *valore di mercato da costo* (deprezzato +
    suolo), non il valore di ricostruzione a nuovo.
    """
    if not method_values:
        raise ValueError("Nessun metodo disponibile per la riconciliazione")

    base = DEFAULT_WEIGHTS.get(purpose, DEFAULT_WEIGHTS[ValuationPurpose.MARKET])
    raw = {m: base.get(m, 0.0) for m in method_values}
    total = sum(raw.values())

    notes: list[str] = []
    if total <= 0:
        # Nessuno dei metodi disponibili e' previsto per questa finalita':
        # ripartizione uniforme.
        raw = {m: 1.0 for m in method_values}
        total = sum(raw.values())
        notes.append("Pesi uniformi: i metodi disponibili non rientrano nel profilo della finalita'.")

    weights = {m: w / total for m, w in raw.items()}
    market_value = sum(method_values[m] * weights[m] for m in method_values)

    if len(method_values) == 1:
        only = next(iter(method_values))
        notes.append(f"Valore basato sul solo metodo: {only.value}.")

    return ReconciliationResult(
        method_values={m.value: round_money(v) for m, v in method_values.items()},
        weights={m.value: round(w, 4) for m, w in weights.items()},
        market_value=round_money(market_value),
        notes=notes,
    )
