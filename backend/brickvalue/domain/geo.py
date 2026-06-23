"""Modelli per geolocalizzazione e parametri inferiti dall'indirizzo."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GeoLocation(BaseModel):
    """Esito della risoluzione di un indirizzo (Google Maps o fallback testuale)."""

    query: str = Field(description="Indirizzo richiesto")
    source: str = Field(description="'google' | 'fallback_testuale' | 'sconosciuto'")
    formatted_address: str | None = None
    municipality: str | None = None
    province: str | None = None
    region: str | None = None
    postal_code: str | None = None
    lat: float | None = None
    lng: float | None = None
    location_type: str | None = Field(
        default=None, description="Precisione Google (ROOFTOP, APPROXIMATE, ...)"
    )
    partial_match: bool = False


class InferredParameters(BaseModel):
    """Parametri di stima dedotti dalla localizzazione."""

    base_unit_value: float | None = Field(
        default=None, description="Valore unitario di zona dedotto (€/m²)"
    )
    cap_rate: float | None = Field(default=None, description="Saggio di capitalizzazione dedotto")
    construction_cost_multiplier: float = Field(
        default=1.0, description="Moltiplicatore regionale del costo di costruzione"
    )
    centrality_multiplier: float | None = Field(
        default=None, description="Moltiplicatore di centralita' applicato"
    )
    distance_to_center_km: float | None = None
    city: str | None = None
    region: str | None = None
    confidence: str = Field(default="bassa", description="'alta' | 'media' | 'bassa'")
    notes: list[str] = Field(default_factory=list)


class GeoLookupResult(BaseModel):
    """Localizzazione + parametri inferiti."""

    location: GeoLocation
    parameters: InferredParameters
