"""Modelli di output: risultati dei metodi e report di valutazione."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from brickvalue.domain.enums import (
    SurfaceComponentType,
    ValuationMethod,
    ValuationPurpose,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Superficie commerciale
# ---------------------------------------------------------------------------
class SurfaceLine(BaseModel):
    """Riga di dettaglio del ragguaglio di una superficie."""

    type: SurfaceComponentType
    label: str | None = None
    area: float
    coefficient: float
    weighted_area: float


class SurfaceResult(BaseModel):
    """Esito del calcolo della superficie commerciale."""

    lines: list[SurfaceLine]
    main_area: float = Field(description="Superficie principale (m²)")
    wall_incidence_pct: float = 0.0
    wall_area_added: float = 0.0
    commercial_surface: float = Field(description="Superficie commerciale ragguagliata (m²)")


# ---------------------------------------------------------------------------
# Deprezzamento
# ---------------------------------------------------------------------------
class DepreciationResult(BaseModel):
    """Esito del calcolo del deprezzamento (Ross-Heidecke)."""

    method: str = "ross-heidecke"
    age_years: int
    useful_life_years: int
    age_ratio: float
    ross_coefficient: float
    heidecke_coefficient: float
    total_depreciation: float = Field(description="Quota di deprezzamento totale (0-1)")
    residual_ratio: float = Field(description="Quota di valore residuo (1 - deprezzamento)")
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Risultati dei metodi
# ---------------------------------------------------------------------------
class MarketResult(BaseModel):
    """Esito dell'approccio del confronto di mercato."""

    method: ValuationMethod = ValuationMethod.MARKET_COMPARISON
    approach: str = Field(description="'comparables' oppure 'valore_unitario'")
    commercial_surface: float
    base_unit_value: float
    merit_multiplier: float
    merit_breakdown: dict[str, float] = Field(default_factory=dict)
    adjusted_unit_value: float
    value: float
    comparables_detail: list[dict] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class CostResult(BaseModel):
    """Esito dell'approccio del costo / ricostruzione a nuovo."""

    method: ValuationMethod = ValuationMethod.COST
    gross_floor_area: float
    construction_cost_per_sqm: float
    bare_construction_cost: float
    technical_fees: float
    overhead_profit: float
    urbanization_charges: float
    vat: float
    demolition_cost: float
    reconstruction_cost_new: float = Field(
        description="Valore di ricostruzione a nuovo (assicurativo), senza suolo ne' deprezzamento"
    )
    depreciation: DepreciationResult | None = None
    depreciated_construction_value: float
    land_value: float
    market_value_via_cost: float = Field(
        description="Valore di mercato da costo (deprezzato + suolo)"
    )
    notes: list[str] = Field(default_factory=list)


class IncomeResult(BaseModel):
    """Esito dell'approccio reddituale (capitalizzazione diretta)."""

    method: ValuationMethod = ValuationMethod.INCOME
    potential_gross_income: float
    effective_gross_income: float
    operating_expenses: float
    net_operating_income: float
    cap_rate: float
    gross_yield: float
    value: float
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Riconciliazione e report finale
# ---------------------------------------------------------------------------
class ReconciliationResult(BaseModel):
    """Sintesi dei valori dei diversi metodi (media ponderata)."""

    method_values: dict[str, float] = Field(default_factory=dict)
    weights: dict[str, float] = Field(default_factory=dict)
    market_value: float
    notes: list[str] = Field(default_factory=list)


class ValueRange(BaseModel):
    """Intervallo di valore (minimo, piu' probabile, massimo)."""

    min: float
    most_likely: float
    max: float


class ValuationReport(BaseModel):
    """Report completo di valutazione."""

    currency: str = "EUR"
    purpose: ValuationPurpose
    generated_at: datetime = Field(default_factory=_utcnow)

    surface: SurfaceResult
    market: MarketResult | None = None
    cost: CostResult | None = None
    income: IncomeResult | None = None
    reconciliation: ReconciliationResult

    # Valori di sintesi
    market_value: float = Field(description="Valore di mercato/commerciale (€)")
    unit_market_value: float = Field(description="Valore unitario (€/m² di superficie commerciale)")
    reconstruction_value_new: float | None = Field(
        default=None, description="Valore di ricostruzione a nuovo per finalita' assicurative (€)"
    )
    forced_sale_value: float = Field(description="Valore di pronto realizzo / vendita forzata (€)")
    mortgage_lending_value: float = Field(description="Valore cauzionale prudenziale (€)")
    value_range: ValueRange

    recommended_value: float = Field(description="Valore consigliato in base alla finalita' (€)")
    recommended_value_label: str

    warnings: list[str] = Field(default_factory=list)
    methodology_notes: list[str] = Field(default_factory=list)
