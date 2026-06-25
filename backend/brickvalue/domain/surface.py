"""Modelli di input per il calcolo della superficie commerciale."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from brickvalue.domain.enums import SurfaceComponentType


class SurfaceComponent(BaseModel):
    """Una componente di superficie (es. principale, balcone, cantina)."""

    model_config = ConfigDict(extra="forbid")

    type: SurfaceComponentType = Field(description="Tipo di superficie")
    area: float = Field(ge=0, le=1_000_000, description="Superficie reale in m²")
    coefficient: float | None = Field(
        default=None,
        ge=0,
        le=2,
        description="Coefficiente di ragguaglio; se assente usa il default di riferimento",
    )
    label: str | None = Field(default=None, max_length=120, description="Descrizione libera")

    @field_validator("area")
    @classmethod
    def _finite_area(cls, v: float) -> float:
        if v != v or v in (float("inf"), float("-inf")):  # NaN o infinito
            raise ValueError("La superficie deve essere un numero finito")
        return v


class SurfaceInput(BaseModel):
    """Insieme delle componenti di superficie dell'immobile."""

    model_config = ConfigDict(extra="forbid")

    components: list[SurfaceComponent] = Field(
        default_factory=list, description="Elenco delle superfici da ragguagliare"
    )
    wall_incidence_pct: float = Field(
        default=0.0,
        ge=0.0,
        le=0.5,
        description=(
            "Incidenza dei muri da aggiungere alla superficie principale "
            "(es. 0.10 = +10%). Usare 0 se l'area inserita e' gia' commerciale."
        ),
    )

    @field_validator("components")
    @classmethod
    def _non_empty(cls, v: list[SurfaceComponent]) -> list[SurfaceComponent]:
        if not v:
            raise ValueError("Inserire almeno una componente di superficie")
        return v

    @property
    def main_area(self) -> float:
        """Superficie principale totale (somma delle componenti MAIN)."""
        return sum(
            c.area for c in self.components if c.type == SurfaceComponentType.MAIN
        )
