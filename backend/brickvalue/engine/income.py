"""Approccio reddituale: capitalizzazione diretta del reddito.

    V = NOI / r

dove NOI e' il reddito operativo netto annuo e r il saggio di capitalizzazione.
"""

from __future__ import annotations

from brickvalue.data.reference import cap_rate_for
from brickvalue.domain.inputs import ValuationRequest
from brickvalue.domain.results import IncomeResult, SurfaceResult
from brickvalue.utils import round_money, safe_div


def compute_income(req: ValuationRequest, surface: SurfaceResult) -> IncomeResult:
    """Calcola il valore con l'approccio reddituale."""
    if req.income is None:  # pragma: no cover - difensivo
        raise ValueError("Parametri reddituali assenti")

    inc = req.income
    notes: list[str] = []

    # Reddito lordo potenziale annuo
    if inc.annual_gross_income is not None:
        pgi = inc.annual_gross_income
    elif inc.monthly_rent is not None:
        pgi = inc.monthly_rent * 12.0
    else:
        pgi = inc.market_rent_per_sqm_month * surface.commercial_surface * 12.0
        notes.append("Reddito stimato dal canone di mercato unitario sulla superficie commerciale.")

    # Reddito effettivo (al netto dello sfitto)
    egi = pgi * (1.0 - inc.vacancy_rate)

    # Spese di gestione
    if inc.operating_expenses_abs is not None:
        opex = inc.operating_expenses_abs
    else:
        opex = egi * inc.operating_expenses_pct

    noi = egi - opex
    if noi < 0:
        noi = 0.0
        notes.append("Spese superiori al reddito effettivo: reddito netto azzerato.")

    cap = inc.cap_rate if inc.cap_rate is not None else cap_rate_for(req.property.property_type)
    if inc.cap_rate is None:
        notes.append("Saggio di capitalizzazione da dati di riferimento.")

    value = safe_div(noi, cap)
    gross_yield = safe_div(pgi, value) if value > 0 else 0.0

    return IncomeResult(
        potential_gross_income=round_money(pgi),
        effective_gross_income=round_money(egi),
        operating_expenses=round_money(opex),
        net_operating_income=round_money(noi),
        cap_rate=round(cap, 4),
        gross_yield=round(gross_yield, 4),
        value=round_money(value),
        notes=notes,
    )
