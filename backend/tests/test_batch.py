"""Test della stima massiva (batch)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from brickvalue.domain.batch import BatchItem, BatchValuationRequest
from brickvalue.engine.batch import compute_batch


def test_batch_mixed_sources():
    req = BatchValuationRequest(
        items=[
            BatchItem(label="A", area_sqm=100, base_unit_value=2000),
            BatchItem(label="B", area_sqm=80, address="Via Roma, Milano"),
            BatchItem(label="C", area_sqm=90, address="Desenzano del Garda"),
        ]
    )
    res = compute_batch(req)
    assert res.count == 3
    assert res.ok == 3
    assert res.errors == 0
    assert len(res.items) == 3
    # A: 100 * 2000 * merito (normale=1.0) = 200000
    a = res.items[0]
    assert a.market_value == pytest.approx(200000.0)
    assert a.reconstruction_value_new is not None
    # B: dedotto da Milano
    b = res.items[1]
    assert b.city == "Milano"
    assert b.market_value > 0
    # C: comune piccolo riconosciuto
    assert res.items[2].city == "Desenzano del Garda"
    assert res.total_market_value > 0


def test_batch_totals_sum():
    req = BatchValuationRequest(
        items=[
            BatchItem(area_sqm=100, base_unit_value=2000),
            BatchItem(area_sqm=50, base_unit_value=3000),
        ]
    )
    res = compute_batch(req)
    expected = sum(i.market_value for i in res.items)
    assert res.total_market_value == pytest.approx(expected)


def test_batch_requires_items():
    with pytest.raises(ValidationError):
        BatchValuationRequest(items=[])


def test_batch_item_requires_area():
    with pytest.raises(ValidationError):
        BatchItem(address="Milano")
