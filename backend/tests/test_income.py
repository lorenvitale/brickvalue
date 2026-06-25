"""Test dell'approccio reddituale."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from brickvalue.domain.enums import PropertyType
from brickvalue.domain.inputs import IncomeInput, ValuationRequest
from brickvalue.domain.property import PropertyInput
from brickvalue.domain.surface import SurfaceComponent, SurfaceInput
from brickvalue.engine.income import compute_income
from brickvalue.engine.surface import compute_surface


def _request(income: IncomeInput, ptype=PropertyType.APARTMENT) -> tuple[ValuationRequest, object]:
    prop = PropertyInput(property_type=ptype)
    surface = SurfaceInput(components=[SurfaceComponent(type="superficie_principale", area=100.0)])
    req = ValuationRequest(property=prop, surface=surface, income=income)
    return req, compute_surface(surface)


def test_annual_income_capitalization():
    income = IncomeInput(
        annual_gross_income=12000.0,
        vacancy_rate=0.0,
        operating_expenses_pct=0.0,
        cap_rate=0.04,
    )
    req, surf = _request(income)
    res = compute_income(req, surf)
    # NOI = 12000, V = 12000 / 0.04 = 300000
    assert res.net_operating_income == pytest.approx(12000.0)
    assert res.value == pytest.approx(300000.0)


def test_monthly_rent_annualized():
    income = IncomeInput(monthly_rent=1000.0, vacancy_rate=0.0,
                         operating_expenses_pct=0.0, cap_rate=0.05)
    req, surf = _request(income)
    res = compute_income(req, surf)
    assert res.potential_gross_income == pytest.approx(12000.0)
    assert res.value == pytest.approx(240000.0)


def test_rent_per_sqm():
    income = IncomeInput(market_rent_per_sqm_month=10.0, vacancy_rate=0.0,
                         operating_expenses_pct=0.0, cap_rate=0.05)
    req, surf = _request(income)
    res = compute_income(req, surf)
    # 10 * 100 * 12 = 12000
    assert res.potential_gross_income == pytest.approx(12000.0)


def test_vacancy_and_opex():
    income = IncomeInput(
        annual_gross_income=10000.0,
        vacancy_rate=0.10,
        operating_expenses_pct=0.20,
        cap_rate=0.05,
    )
    req, surf = _request(income)
    res = compute_income(req, surf)
    # EGI = 9000; opex = 1800; NOI = 7200; V = 144000
    assert res.effective_gross_income == pytest.approx(9000.0)
    assert res.operating_expenses == pytest.approx(1800.0)
    assert res.net_operating_income == pytest.approx(7200.0)
    assert res.value == pytest.approx(144000.0)


def test_absolute_opex_overrides_pct():
    income = IncomeInput(
        annual_gross_income=10000.0,
        vacancy_rate=0.0,
        operating_expenses_pct=0.50,
        operating_expenses_abs=1000.0,
        cap_rate=0.05,
    )
    req, surf = _request(income)
    res = compute_income(req, surf)
    assert res.operating_expenses == pytest.approx(1000.0)
    assert res.net_operating_income == pytest.approx(9000.0)


def test_default_cap_rate_used():
    income = IncomeInput(annual_gross_income=10000.0, vacancy_rate=0.0, operating_expenses_pct=0.0)
    req, surf = _request(income, ptype=PropertyType.OFFICE)
    res = compute_income(req, surf)
    # ufficio cap rate riferimento = 0.055
    assert res.cap_rate == pytest.approx(0.055)


def test_negative_noi_clamped_to_zero():
    income = IncomeInput(
        annual_gross_income=10000.0,
        vacancy_rate=0.0,
        operating_expenses_abs=15000.0,
        cap_rate=0.05,
    )
    req, surf = _request(income)
    res = compute_income(req, surf)
    assert res.net_operating_income == 0.0
    assert res.value == 0.0


def test_income_requires_source():
    with pytest.raises(ValidationError):
        IncomeInput()
