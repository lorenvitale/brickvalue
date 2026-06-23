"""Test della riconciliazione dei valori."""

from __future__ import annotations

import pytest

from brickvalue.domain.enums import ValuationMethod, ValuationPurpose
from brickvalue.engine.reconciliation import reconcile

_M = ValuationMethod


def test_market_purpose_weights():
    values = {
        _M.MARKET_COMPARISON: 300000.0,
        _M.INCOME: 280000.0,
        _M.COST: 250000.0,
    }
    res = reconcile(ValuationPurpose.MARKET, values)
    # 300000*0.7 + 280000*0.2 + 250000*0.1 = 210000 + 56000 + 25000 = 291000
    assert res.market_value == pytest.approx(291000.0)
    assert res.weights["confronto_di_mercato"] == pytest.approx(0.70)


def test_single_method_uses_full_weight():
    res = reconcile(ValuationPurpose.MARKET, {_M.MARKET_COMPARISON: 200000.0})
    assert res.market_value == pytest.approx(200000.0)
    assert res.weights["confronto_di_mercato"] == pytest.approx(1.0)


def test_weights_normalized_over_available():
    # Solo mercato e reddito disponibili: pesi 0.7 e 0.2 -> normalizzati a 0.778 e 0.222
    values = {_M.MARKET_COMPARISON: 300000.0, _M.INCOME: 200000.0}
    res = reconcile(ValuationPurpose.MARKET, values)
    assert res.weights["confronto_di_mercato"] == pytest.approx(0.7 / 0.9, abs=1e-3)
    assert res.weights["capitalizzazione_reddito"] == pytest.approx(0.2 / 0.9, abs=1e-3)
    total = sum(res.weights.values())
    assert total == pytest.approx(1.0)


def test_insurance_purpose_favours_cost():
    values = {_M.MARKET_COMPARISON: 300000.0, _M.COST: 200000.0}
    res = reconcile(ValuationPurpose.INSURANCE, values)
    # cost peso 0.8, market 0.2
    assert res.weights["costo_di_ricostruzione"] == pytest.approx(0.8)
    assert res.market_value == pytest.approx(300000.0 * 0.2 + 200000.0 * 0.8)


def test_uniform_fallback_when_purpose_excludes_methods():
    # Finalita' assicurativa con solo metodo reddituale (non previsto): pesi uniformi
    res = reconcile(ValuationPurpose.INSURANCE, {_M.INCOME: 220000.0})
    assert res.market_value == pytest.approx(220000.0)
    assert any("uniformi" in n.lower() for n in res.notes)


def test_empty_raises():
    with pytest.raises(ValueError):
        reconcile(ValuationPurpose.MARKET, {})
