"""Modelli per la stima massiva (batch) da un elenco di immobili."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from brickvalue.domain.enums import ConservationState, PropertyType, ValuationPurpose


class BatchItem(BaseModel):
    """Una riga dell'elenco da valutare."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, max_length=160, description="Riferimento libero")
    address: str | None = Field(default=None, max_length=300, description="Indirizzo")
    property_type: PropertyType = Field(default=PropertyType.APARTMENT)
    area_sqm: float = Field(gt=0, le=1_000_000, description="Superficie (m²)")
    purpose: ValuationPurpose = Field(default=ValuationPurpose.MARKET)
    condition: ConservationState = Field(default=ConservationState.NORMAL)
    year_built: int | None = Field(default=None, ge=1000, le=2100)
    base_unit_value: float | None = Field(
        default=None, gt=0, description="Valore di zona (€/m²); se assente dedotto dall'indirizzo"
    )


class BatchValuationRequest(BaseModel):
    """Elenco di immobili da valutare in blocco."""

    model_config = ConfigDict(extra="forbid")

    items: list[BatchItem] = Field(min_length=1, max_length=500)


class BatchItemResult(BaseModel):
    """Esito di una riga."""

    label: str | None = None
    address: str | None = None
    city: str | None = None
    region: str | None = None
    purpose: ValuationPurpose
    commercial_surface: float | None = None
    unit_value: float | None = None
    market_value: float | None = None
    reconstruction_value_new: float | None = None
    recommended_value: float | None = None
    recommended_label: str | None = None
    confidence: str | None = None
    error: str | None = None


class BatchResult(BaseModel):
    """Esito complessivo della stima massiva."""

    count: int
    ok: int
    errors: int
    total_market_value: float = 0.0
    total_reconstruction_value: float = 0.0
    items: list[BatchItemResult]
