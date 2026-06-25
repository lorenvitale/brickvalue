"""Funzioni di utilità condivise (arrotondamenti monetari e di superficie).

In una stima i valori sono per natura approssimati: per evitare la propagazione
di errori di virgola mobile e rendere i risultati riproducibili, gli importi
vengono arrotondati in modo deterministico ai punti di confine (output).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def round_money(value: float, decimals: int = 2) -> float:
    """Arrotonda un importo monetario con arrotondamento commerciale (half-up).

    >>> round_money(1234.565)
    1234.57
    >>> round_money(1234.564)
    1234.56
    """
    if value is None:  # pragma: no cover - difensivo
        raise ValueError("value non puo' essere None")
    quant = Decimal(1).scaleb(-decimals)
    return float(Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP))


def round_area(value: float, decimals: int = 2) -> float:
    """Arrotonda una superficie (m²) con arrotondamento commerciale."""
    return round_money(value, decimals)


def round_rate(value: float, decimals: int = 4) -> float:
    """Arrotonda un saggio/coefficiente (es. tasso di capitalizzazione)."""
    return round_money(value, decimals)


def clamp(value: float, low: float, high: float) -> float:
    """Vincola ``value`` nell'intervallo ``[low, high]``."""
    if low > high:  # pragma: no cover - difensivo
        raise ValueError("low non puo' essere maggiore di high")
    return max(low, min(high, value))


def safe_div(numerator: float, denominator: float) -> float:
    """Divisione che solleva un errore chiaro in caso di denominatore nullo."""
    if denominator == 0:
        raise ZeroDivisionError("divisione per zero non ammessa nel calcolo")
    return numerator / denominator


def product(values: list[float]) -> float:
    """Prodotto di una lista di fattori (1.0 se vuota)."""
    result = 1.0
    for v in values:
        result *= v
    return result
