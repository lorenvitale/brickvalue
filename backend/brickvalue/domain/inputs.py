"""Modelli di input dei singoli metodi di stima e della richiesta complessiva."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from brickvalue.domain.enums import ValuationMethod, ValuationPurpose
from brickvalue.domain.property import PropertyInput
from brickvalue.domain.surface import SurfaceInput


# ---------------------------------------------------------------------------
# Confronto di mercato
# ---------------------------------------------------------------------------
class Comparable(BaseModel):
    """Immobile comparabile per l'approccio del confronto di mercato (MCA)."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, max_length=120)
    price: float = Field(gt=0, description="Prezzo del comparabile (€)")
    commercial_surface: float = Field(gt=0, description="Superficie commerciale del comparabile (m²)")
    net_adjustment: float = Field(
        default=0.0,
        ge=-0.9,
        le=2.0,
        description=(
            "Aggiustamento netto percentuale applicato al comparabile per "
            "renderlo omogeneo al subject (es. +0.05 = +5%)"
        ),
    )
    weight: float = Field(default=1.0, gt=0, le=100, description="Peso relativo del comparabile")

    @property
    def unit_price(self) -> float:
        return self.price / self.commercial_surface

    @property
    def adjusted_unit_price(self) -> float:
        return self.unit_price * (1.0 + self.net_adjustment)


class MarketInput(BaseModel):
    """Parametri per l'approccio del confronto di mercato."""

    model_config = ConfigDict(extra="forbid")

    base_unit_value: float | None = Field(
        default=None,
        gt=0,
        description="Valore unitario di mercato di zona (€/m² di superficie commerciale)",
    )
    comparables: list[Comparable] = Field(default_factory=list)

    apply_conservation_merit: bool = Field(
        default=True, description="Applica il coefficiente per stato di conservazione"
    )
    apply_energy_merit: bool = Field(
        default=True, description="Applica il coefficiente per classe energetica"
    )
    apply_floor_merit: bool = Field(
        default=True, description="Applica il coefficiente per piano/ascensore"
    )
    extra_coefficients: list[float] = Field(
        default_factory=list,
        description="Coefficienti di merito aggiuntivi (es. esposizione, vista, posizione)",
    )

    @model_validator(mode="after")
    def _has_source(self) -> "MarketInput":
        if self.base_unit_value is None and not self.comparables:
            raise ValueError(
                "Il confronto di mercato richiede 'base_unit_value' oppure dei 'comparables'"
            )
        for c in self.extra_coefficients:
            if c <= 0 or c > 3:
                raise ValueError("I coefficienti di merito devono essere in (0, 3]")
        return self


# ---------------------------------------------------------------------------
# Costo di ricostruzione
# ---------------------------------------------------------------------------
class CostInput(BaseModel):
    """Parametri per l'approccio del costo / valore di ricostruzione a nuovo."""

    model_config = ConfigDict(extra="forbid")

    gross_floor_area: float | None = Field(
        default=None,
        gt=0,
        description="Superficie lorda (m²); se assente derivata dalla superficie principale",
    )
    construction_cost_per_sqm: float | None = Field(
        default=None, gt=0, description="Costo di costruzione a nuovo (€/m²)"
    )
    technical_fees_pct: float = Field(
        default=0.10, ge=0, le=0.5, description="Spese tecniche e professionali (quota)"
    )
    overhead_profit_pct: float = Field(
        default=0.12, ge=0, le=0.6, description="Spese generali e utile del costruttore (quota)"
    )
    urbanization_charges: float = Field(
        default=0.0, ge=0, description="Oneri di urbanizzazione/concessori (€, assoluti)"
    )
    vat_pct: float = Field(default=0.0, ge=0, le=0.3, description="IVA sul costo (quota)")
    demolition_cost: float = Field(
        default=0.0, ge=0, description="Costi di demolizione/sgombero per ricostruzione (€)"
    )
    land_value: float | None = Field(
        default=None, ge=0, description="Valore del suolo/area (€) per il valore di mercato da costo"
    )
    useful_life_years: int | None = Field(
        default=None, gt=0, le=300, description="Vita utile (anni); se assente da tipologia struttura"
    )


# ---------------------------------------------------------------------------
# Capitalizzazione del reddito
# ---------------------------------------------------------------------------
class IncomeInput(BaseModel):
    """Parametri per l'approccio reddituale (capitalizzazione diretta)."""

    model_config = ConfigDict(extra="forbid")

    annual_gross_income: float | None = Field(
        default=None, gt=0, description="Reddito lordo annuo (€)"
    )
    monthly_rent: float | None = Field(default=None, gt=0, description="Canone mensile (€)")
    market_rent_per_sqm_month: float | None = Field(
        default=None, gt=0, description="Canone di mercato (€/m² al mese) sulla superficie commerciale"
    )
    vacancy_rate: float = Field(
        default=0.05, ge=0, le=0.9, description="Tasso di sfitto/morosita'"
    )
    operating_expenses_pct: float = Field(
        default=0.20, ge=0, le=0.9, description="Spese di gestione (quota del reddito effettivo)"
    )
    operating_expenses_abs: float | None = Field(
        default=None, ge=0, description="Spese di gestione assolute (€); prevalgono sulla quota"
    )
    cap_rate: float | None = Field(
        default=None, gt=0, le=0.5, description="Saggio di capitalizzazione; se assente da tipologia"
    )

    @model_validator(mode="after")
    def _has_income(self) -> "IncomeInput":
        if (
            self.annual_gross_income is None
            and self.monthly_rent is None
            and self.market_rent_per_sqm_month is None
        ):
            raise ValueError(
                "L'approccio reddituale richiede un reddito (annuo, mensile o €/m²/mese)"
            )
        return self


# ---------------------------------------------------------------------------
# Richiesta complessiva
# ---------------------------------------------------------------------------
class ValuationRequest(BaseModel):
    """Richiesta completa di valutazione."""

    model_config = ConfigDict(extra="forbid")

    property: PropertyInput
    surface: SurfaceInput
    purpose: ValuationPurpose = Field(default=ValuationPurpose.MARKET)

    market: MarketInput | None = None
    cost: CostInput | None = None
    income: IncomeInput | None = None

    methods: list[ValuationMethod] | None = Field(
        default=None,
        description="Metodi da eseguire; se assente vengono selezionati automaticamente",
    )

    reference_year: int | None = Field(
        default=None, ge=1900, le=2200, description="Anno di riferimento per il calcolo dell'eta'"
    )
    value_range_pct: float = Field(
        default=0.10, ge=0, le=0.5, description="Semi-ampiezza dell'intervallo di valore (±)"
    )
    forced_sale_haircut: float = Field(
        default=0.15, ge=0, le=0.6, description="Riduzione per valore di pronto realizzo (vendita forzata)"
    )
    mortgage_prudence_haircut: float = Field(
        default=0.10, ge=0, le=0.5, description="Riduzione prudenziale per il valore cauzionale"
    )
