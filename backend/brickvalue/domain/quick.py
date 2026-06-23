"""Modello della valutazione rapida ("versione base").

Pensato per l'utente finale non tecnico: pochi campi, guidati dall'obiettivo
(assicurazione, vendita, mutuo). I valori vengono poi espansi in una
:class:`~brickvalue.domain.inputs.ValuationRequest` completa dal motore.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from brickvalue.domain.enums import PropertyType


class QuickGoal(str, Enum):
    """Obiettivo finale dell'utente (determina il valore mostrato)."""

    INSURANCE = "assicurazione"  # valore di ricostruzione a nuovo
    MARKET = "vendita"  # valore di mercato
    BANKING = "mutuo"  # valore cauzionale


class BuildingScope(str, Enum):
    """Oggetto della valutazione."""

    UNIT = "unita"  # singola unita'/porzione -> metri quadri
    BUILDING = "edificio"  # intero fabbricato/condominio -> numero di unita'


class SimpleCondition(str, Enum):
    """Stato dell'immobile in linguaggio semplice."""

    AS_NEW = "come_nuovo"
    GOOD = "buono"
    TO_FIX = "da_sistemare"


class QuickValuationRequest(BaseModel):
    """Richiesta semplificata della versione base."""

    model_config = ConfigDict(extra="forbid")

    goal: QuickGoal = Field(description="Cosa serve all'utente")
    scope: BuildingScope = Field(default=BuildingScope.UNIT, description="Unita' o intero edificio")
    property_type: PropertyType = Field(
        default=PropertyType.APARTMENT, description="Tipo di immobile (singola unita')"
    )

    address: str | None = Field(default=None, max_length=300, description="Indirizzo completo")
    floor: int | None = Field(default=None, ge=-5, le=200, description="Piano (per singola unita')")
    total_floors: int | None = Field(default=None, ge=0, le=200, description="Numero di piani")

    # Singola unita'
    area_sqm: float | None = Field(
        default=None, gt=0, le=1_000_000, description="Metri quadri (per singola unita')"
    )
    # Intero edificio
    num_units: int | None = Field(
        default=None, gt=0, le=10_000, description="Numero di unita' immobiliari (per edificio)"
    )
    avg_unit_sqm: float = Field(
        default=90.0, gt=0, le=10_000, description="Dimensione media per unita' (m²)"
    )

    year_built: int | None = Field(
        default=None, ge=1000, le=2100, description="Anno di costruzione (circa)"
    )
    condition: SimpleCondition = Field(default=SimpleCondition.GOOD, description="Stato dell'immobile")

    base_unit_value: float | None = Field(
        default=None,
        gt=0,
        description="Prezzo medio di zona (€/m²), necessario per vendita/mutuo",
    )

    @model_validator(mode="after")
    def _check(self) -> "QuickValuationRequest":
        if self.scope == BuildingScope.UNIT and self.area_sqm is None:
            raise ValueError("Indicare i metri quadri dell'immobile")
        if self.scope == BuildingScope.BUILDING and self.num_units is None:
            raise ValueError("Indicare il numero di unita' immobiliari")
        if self.goal in (QuickGoal.MARKET, QuickGoal.BANKING) and self.base_unit_value is None:
            raise ValueError(
                "Per il valore di vendita/mutuo indicare il prezzo medio di zona (€/m²)"
            )
        if self.total_area > 1_000_000:
            raise ValueError(
                "Valori troppo elevati: controlla il numero di unita' e la dimensione media"
            )
        return self

    @property
    def total_area(self) -> float:
        """Superficie totale considerata (m²)."""
        if self.scope == BuildingScope.BUILDING:
            return float(self.num_units) * self.avg_unit_sqm
        return float(self.area_sqm)
