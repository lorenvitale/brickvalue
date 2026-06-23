"""Orchestratore della valutazione: seleziona i metodi, li esegue e produce il
report completo con i valori di sintesi per ciascuna finalita'.
"""

from __future__ import annotations

from brickvalue.domain.enums import ValuationMethod, ValuationPurpose
from brickvalue.domain.inputs import ValuationRequest
from brickvalue.domain.results import (
    CostResult,
    IncomeResult,
    MarketResult,
    ValuationReport,
    ValueRange,
)
from brickvalue.engine.cost import compute_cost
from brickvalue.engine.income import compute_income
from brickvalue.engine.market import compute_market
from brickvalue.engine.reconciliation import reconcile
from brickvalue.engine.surface import compute_surface
from brickvalue.utils import round_money, safe_div

_M = ValuationMethod


def _select_methods(req: ValuationRequest, warnings: list[str]) -> set[ValuationMethod]:
    """Determina i metodi da eseguire (espliciti o selezionati automaticamente)."""
    is_land = req.property.property_type.is_land
    can_market = req.market is not None
    can_income = req.income is not None
    can_cost = not is_land

    if req.methods is not None:
        requested = set(req.methods)
    else:
        requested = set()
        if can_market:
            requested.add(_M.MARKET_COMPARISON)
        if can_income:
            requested.add(_M.INCOME)
        if can_cost and (
            req.cost is not None
            or req.purpose in (ValuationPurpose.INSURANCE, ValuationPurpose.TECHNICAL)
        ):
            requested.add(_M.COST)
        if not requested and can_cost:
            requested.add(_M.COST)

    # La finalita' assicurativa/tecnica richiede il metodo del costo
    if req.purpose in (ValuationPurpose.INSURANCE, ValuationPurpose.TECHNICAL) and can_cost:
        requested.add(_M.COST)

    selected: set[ValuationMethod] = set()
    for m in requested:
        if m == _M.MARKET_COMPARISON and not can_market:
            warnings.append("Confronto di mercato richiesto ma parametri di mercato assenti: ignorato.")
        elif m == _M.INCOME and not can_income:
            warnings.append("Metodo reddituale richiesto ma reddito assente: ignorato.")
        elif m == _M.COST and not can_cost:
            warnings.append("Metodo del costo non applicabile (terreno): ignorato.")
        else:
            selected.add(m)
    return selected


def _recommended(
    purpose: ValuationPurpose,
    market_value: float,
    reconstruction_new: float | None,
    mortgage_value: float,
    cost_res: CostResult | None,
) -> tuple[float, str]:
    """Valore consigliato ed etichetta in base alla finalita'."""
    if purpose == ValuationPurpose.INSURANCE:
        if reconstruction_new is not None:
            return reconstruction_new, "Valore di ricostruzione a nuovo (assicurativo)"
        return market_value, "Valore di mercato (ricostruzione non calcolabile)"
    if purpose == ValuationPurpose.BANKING:
        return mortgage_value, "Valore cauzionale (bancario)"
    if purpose == ValuationPurpose.TECHNICAL:
        if cost_res is not None:
            return cost_res.market_value_via_cost, "Valore tecnico da costo"
        return market_value, "Valore di mercato"
    if purpose == ValuationPurpose.LEGAL:
        return market_value, "Valore di mercato (uso legale)"
    return market_value, "Valore di mercato (commerciale)"


def valuate(req: ValuationRequest) -> ValuationReport:
    """Esegue la valutazione completa e restituisce il report.

    Flusso:

    1. calcolo della superficie commerciale;
    2. selezione ed esecuzione dei metodi applicabili;
    3. riconciliazione in valore di mercato;
    4. derivazione dei valori di sintesi (ricostruzione a nuovo, pronto realizzo,
       cauzionale) e del valore consigliato per la finalita'.
    """
    warnings: list[str] = []
    methodology: list[str] = []

    surface = compute_surface(req.surface)
    if surface.commercial_surface <= 0:
        raise ValueError("La superficie commerciale calcolata e' nulla: verificare le superfici")

    selected = _select_methods(req, warnings)

    market_res: MarketResult | None = None
    cost_res: CostResult | None = None
    income_res: IncomeResult | None = None

    if _M.MARKET_COMPARISON in selected:
        market_res = compute_market(req, surface)
        methodology.append("Confronto di mercato: valore = superficie commerciale × valore unitario.")
    if _M.COST in selected:
        cost_res = compute_cost(req, surface)
        methodology.append(
            "Costo: ricostruzione a nuovo (assicurativo) e valore di mercato da costo "
            "(deprezzato Ross-Heidecke + suolo)."
        )
    if _M.INCOME in selected:
        income_res = compute_income(req, surface)
        methodology.append("Reddituale: valore = reddito operativo netto / saggio di capitalizzazione.")

    # Valori che concorrono alla riconciliazione in valore di mercato.
    recon_values: dict[ValuationMethod, float] = {}
    if market_res is not None:
        recon_values[_M.MARKET_COMPARISON] = market_res.value
    if income_res is not None:
        recon_values[_M.INCOME] = income_res.value
    if cost_res is not None and cost_res.land_value > 0:
        recon_values[_M.COST] = cost_res.market_value_via_cost

    if not recon_values:
        if cost_res is not None:
            recon_values[_M.COST] = cost_res.market_value_via_cost
            warnings.append(
                "Valore di mercato stimato col solo metodo del costo: senza valore del suolo "
                "il risultato e' incompleto e tendenzialmente prudenziale."
            )
        else:
            raise ValueError(
                "Dati insufficienti per la stima: fornire parametri di mercato, reddito o costo"
            )

    reconciliation = reconcile(req.purpose, recon_values)
    market_value = reconciliation.market_value

    reconstruction_new = cost_res.reconstruction_cost_new if cost_res is not None else None
    if reconstruction_new is None and req.purpose == ValuationPurpose.INSURANCE:
        warnings.append(
            "Finalita' assicurativa ma valore di ricostruzione non calcolabile "
            "(terreno o dati insufficienti)."
        )

    forced_sale_value = round_money(market_value * (1.0 - req.forced_sale_haircut))
    mortgage_value = round_money(market_value * (1.0 - req.mortgage_prudence_haircut))

    unit_value = round_money(safe_div(market_value, surface.commercial_surface))

    value_range = ValueRange(
        min=round_money(market_value * (1.0 - req.value_range_pct)),
        most_likely=round_money(market_value),
        max=round_money(market_value * (1.0 + req.value_range_pct)),
    )

    recommended, recommended_label = _recommended(
        req.purpose, market_value, reconstruction_new, mortgage_value, cost_res
    )

    return ValuationReport(
        purpose=req.purpose,
        surface=surface,
        market=market_res,
        cost=cost_res,
        income=income_res,
        reconciliation=reconciliation,
        market_value=round_money(market_value),
        unit_market_value=unit_value,
        reconstruction_value_new=reconstruction_new,
        forced_sale_value=forced_sale_value,
        mortgage_lending_value=mortgage_value,
        value_range=value_range,
        recommended_value=round_money(recommended),
        recommended_value_label=recommended_label,
        warnings=warnings,
        methodology_notes=methodology,
    )
