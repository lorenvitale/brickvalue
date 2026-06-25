"""Modello dell'immobile da valutare."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from brickvalue.domain.enums import (
    ConservationState,
    EnergyClass,
    PropertyType,
    StructureType,
)


class Location(BaseModel):
    """Localizzazione dell'immobile (informativa, usata nel report)."""

    model_config = ConfigDict(extra="forbid")

    address: str | None = Field(default=None, max_length=200)
    municipality: str | None = Field(default=None, max_length=120)
    province: str | None = Field(default=None, max_length=4)
    zone: str | None = Field(default=None, max_length=120, description="Microzona/OMI")
    cadastral_ref: str | None = Field(default=None, max_length=120, description="Dati catastali")


class PropertyInput(BaseModel):
    """Caratteristiche fisiche e qualitative dell'immobile."""

    model_config = ConfigDict(extra="forbid")

    property_type: PropertyType = Field(description="Tipologia immobiliare")
    structure: StructureType = Field(
        default=StructureType.REINFORCED_CONCRETE, description="Tipologia strutturale"
    )
    conservation: ConservationState = Field(
        default=ConservationState.NORMAL, description="Stato di conservazione"
    )
    energy_class: EnergyClass | None = Field(default=None, description="Classe energetica (APE)")

    year_built: int | None = Field(
        default=None, ge=1000, le=2100, description="Anno di costruzione"
    )
    year_renovated: int | None = Field(
        default=None, ge=1000, le=2100, description="Anno dell'ultima ristrutturazione rilevante"
    )

    floor: int | None = Field(
        default=None, ge=-5, le=200, description="Piano (0 = terra, negativi = interrati)"
    )
    total_floors: int | None = Field(default=None, ge=0, le=200, description="Piani del fabbricato")
    has_elevator: bool = Field(default=False, description="Presenza di ascensore")
    is_penthouse: bool = Field(default=False, description="Attico/ultimo piano pregiato")

    location: Location | None = Field(default=None)

    @model_validator(mode="after")
    def _check_years(self) -> "PropertyInput":
        if (
            self.year_built is not None
            and self.year_renovated is not None
            and self.year_renovated < self.year_built
        ):
            raise ValueError(
                "L'anno di ristrutturazione non puo' precedere l'anno di costruzione"
            )
        if (
            self.floor is not None
            and self.total_floors is not None
            and self.floor > self.total_floors
        ):
            raise ValueError("Il piano non puo' superare il numero di piani del fabbricato")
        return self

    def age(self, reference_year: int | None = None) -> int | None:
        """Eta' effettiva dell'immobile in anni.

        Se presente una ristrutturazione rilevante, l'eta' e' calcolata da
        quella data (eta' "apparente"). Restituisce ``None`` se l'anno di
        costruzione non e' noto.
        """
        if self.year_built is None:
            return None
        ref = reference_year if reference_year is not None else date.today().year
        base_year = self.year_renovated or self.year_built
        return max(0, ref - base_year)
