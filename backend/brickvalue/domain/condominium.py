"""Modelli per la valutazione di un condominio (uso assicurativo).

Calcola il **valore di ricostruzione a nuovo** dell'intero fabbricato e lo
ripartisce per unita' immobiliare (somma da assicurare per ciascun condomino),
per millesimi o per superficie.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator

from brickvalue.domain.enums import StructureType
from brickvalue.domain.geo import GeoLookupResult


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CondoUnit(BaseModel):
    """Unita' immobiliare del condominio."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, max_length=120, description="Es. 'Interno 3, Scala A'")
    surface_sqm: float | None = Field(default=None, gt=0, le=100_000, description="Superficie (m²)")
    millesimi: float | None = Field(default=None, gt=0, le=1000, description="Quota millesimale")
    floor: int | None = Field(default=None, ge=-5, le=200)


class CondominiumRequest(BaseModel):
    """Richiesta di valutazione del valore di ricostruzione di un condominio."""

    model_config = ConfigDict(extra="forbid")

    address: str | None = Field(default=None, max_length=300, description="Indirizzo del fabbricato")
    structure: StructureType = Field(
        default=StructureType.REINFORCED_CONCRETE, description="Tipologia strutturale"
    )
    year_built: int | None = Field(default=None, ge=1000, le=2100, description="Anno (informativo)")

    # Modalita' dettagliata
    units: list[CondoUnit] = Field(default_factory=list, description="Unita' immobiliari")
    # Modalita' aggregata (alternativa)
    total_area_sqm: float | None = Field(
        default=None, gt=0, le=1_000_000, description="Superficie residenziale totale (m²)"
    )
    num_units: int | None = Field(default=None, gt=0, le=10_000, description="Numero di unita'")

    common_area_sqm: float = Field(
        default=0.0, ge=0, le=1_000_000, description="Superficie delle parti comuni (m²)"
    )

    construction_cost_per_sqm: float | None = Field(
        default=None, gt=0, description="Costo di ricostruzione a nuovo (€/m²)"
    )
    technical_fees_pct: float = Field(default=0.10, ge=0, le=0.5, description="Spese tecniche")
    overhead_profit_pct: float = Field(default=0.12, ge=0, le=0.6, description="Spese generali e utile")
    demolition_pct: float = Field(
        default=0.08, ge=0, le=0.4, description="Demolizione e sgombero macerie (quota del costo nudo)"
    )
    vat_pct: float = Field(default=0.0, ge=0, le=0.3, description="IVA")

    auto_parameters: bool = Field(
        default=True, description="Deduci il costo di costruzione regionale dall'indirizzo"
    )

    @model_validator(mode="after")
    def _check(self) -> "CondominiumRequest":
        if self.units:
            if any(u.surface_sqm is None for u in self.units):
                raise ValueError("In modalita' dettagliata ogni unita' deve avere la superficie")
        elif not (self.total_area_sqm and self.num_units):
            raise ValueError(
                "Fornire l'elenco delle unita' (con superficie) oppure superficie totale e numero unita'"
            )
        return self

    @property
    def residential_area(self) -> float:
        if self.units:
            return sum(u.surface_sqm for u in self.units if u.surface_sqm)
        return float(self.total_area_sqm or 0.0)

    @property
    def unit_count(self) -> int:
        return len(self.units) if self.units else int(self.num_units or 0)


class CondoUnitResult(BaseModel):
    """Ripartizione per una singola unita'."""

    label: str
    surface_sqm: float | None = None
    millesimi: float | None = None
    quota_pct: float = Field(description="Quota di partecipazione (0-1)")
    insured_value: float = Field(description="Somma da assicurare per l'unita' (€)")


class CondominiumReport(BaseModel):
    """Esito della valutazione del condominio."""

    currency: str = "EUR"
    generated_at: datetime = Field(default_factory=_utcnow)

    geo: GeoLookupResult | None = None
    region: str | None = None
    construction_cost_per_sqm: float
    regional_multiplier: float = 1.0

    residential_area: float
    common_area: float
    gross_area: float
    unit_count: int

    bare_construction_cost: float
    technical_fees: float
    overhead_profit: float
    demolition_cost: float
    vat: float
    reconstruction_value_new: float = Field(description="Valore di ricostruzione a nuovo totale (€)")
    value_per_sqm: float

    allocation_basis: str = Field(description="'millesimi' | 'superficie' | 'quote_uguali'")
    units: list[CondoUnitResult]

    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
