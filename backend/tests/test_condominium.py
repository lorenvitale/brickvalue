"""Test della valutazione del condominio (uso assicurativo)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from brickvalue.domain.condominium import CondoUnit, CondominiumRequest
from brickvalue.engine.condominium import compute_condominium


def test_detailed_by_millesimi():
    req = CondominiumRequest(
        units=[
            CondoUnit(label="Int 1", surface_sqm=80, millesimi=300),
            CondoUnit(label="Int 2", surface_sqm=100, millesimi=400),
            CondoUnit(label="Int 3", surface_sqm=90, millesimi=300),
        ],
        common_area_sqm=50,
        construction_cost_per_sqm=1500,
        technical_fees_pct=0.10,
        overhead_profit_pct=0.10,
        demolition_pct=0.0,
        auto_parameters=False,
    )
    rep = compute_condominium(req)
    # gross = 80+100+90+50 = 320; bare = 320*1500 = 480000; +20% = 576000
    assert rep.gross_area == pytest.approx(320)
    assert rep.reconstruction_value_new == pytest.approx(576000)
    assert rep.allocation_basis == "millesimi"
    # somma delle quote = totale
    assert sum(u.insured_value for u in rep.units) == pytest.approx(576000, rel=1e-6)
    # unita' 2 ha 400/1000 millesimi
    u2 = rep.units[1]
    assert u2.quota_pct == pytest.approx(0.4)
    assert u2.insured_value == pytest.approx(576000 * 0.4)


def test_allocation_falls_back_to_surface():
    req = CondominiumRequest(
        units=[
            CondoUnit(surface_sqm=100),  # nessun millesimo
            CondoUnit(surface_sqm=300),
        ],
        construction_cost_per_sqm=1000,
        technical_fees_pct=0,
        overhead_profit_pct=0,
        demolition_pct=0,
        auto_parameters=False,
    )
    rep = compute_condominium(req)
    assert rep.allocation_basis == "superficie"
    # 400 m² * 1000 = 400000 ; quote 25% / 75%
    assert rep.units[0].insured_value == pytest.approx(100000)
    assert rep.units[1].insured_value == pytest.approx(300000)


def test_partial_millesimi_warns_and_uses_surface():
    req = CondominiumRequest(
        units=[
            CondoUnit(surface_sqm=100, millesimi=500),
            CondoUnit(surface_sqm=100),  # millesimi mancante
        ],
        construction_cost_per_sqm=1000,
        technical_fees_pct=0, overhead_profit_pct=0, demolition_pct=0,
        auto_parameters=False,
    )
    rep = compute_condominium(req)
    assert rep.allocation_basis == "superficie"
    assert any("Millesimi" in w for w in rep.warnings)


def test_aggregate_equal_split():
    req = CondominiumRequest(
        total_area_sqm=1000,
        num_units=10,
        construction_cost_per_sqm=1200,
        technical_fees_pct=0, overhead_profit_pct=0, demolition_pct=0,
        auto_parameters=False,
    )
    rep = compute_condominium(req)
    assert rep.allocation_basis == "quote_uguali"
    assert len(rep.units) == 10
    # 1000*1200 = 1.2M / 10 = 120000 ciascuna
    assert rep.units[0].insured_value == pytest.approx(120000)


def test_demolition_and_components():
    req = CondominiumRequest(
        total_area_sqm=100, num_units=1,
        construction_cost_per_sqm=1000,
        technical_fees_pct=0.10, overhead_profit_pct=0.10, demolition_pct=0.08,
        auto_parameters=False,
    )
    rep = compute_condominium(req)
    assert rep.bare_construction_cost == pytest.approx(100000)
    assert rep.demolition_cost == pytest.approx(8000)
    # 100000 + 10000 + 10000 + 8000 = 128000
    assert rep.reconstruction_value_new == pytest.approx(128000)


def test_regional_multiplier_from_address():
    req = CondominiumRequest(
        total_area_sqm=1000, num_units=10,
        address="Via Roma, Milano",  # Lombardia -> x1.08
    )
    rep = compute_condominium(req)
    assert rep.region == "Lombardia"
    assert rep.regional_multiplier == pytest.approx(1.08)
    # costo base fabbricato 1300 * 1.08 = 1404
    assert rep.construction_cost_per_sqm == pytest.approx(1404)


def test_explicit_cost_ignores_multiplier():
    req = CondominiumRequest(
        total_area_sqm=100, num_units=1,
        construction_cost_per_sqm=2000, address="Milano",
        technical_fees_pct=0, overhead_profit_pct=0, demolition_pct=0,
    )
    rep = compute_condominium(req)
    assert rep.regional_multiplier == 1.0
    assert rep.construction_cost_per_sqm == 2000


def test_units_require_surface():
    with pytest.raises(ValidationError):
        CondominiumRequest(units=[CondoUnit(millesimi=500)])


def test_requires_units_or_aggregate():
    with pytest.raises(ValidationError):
        CondominiumRequest()
