"""Motore di calcolo della valutazione immobiliare."""

from __future__ import annotations

from brickvalue.engine.autofill import (
    enrich_request,
    lookup_address,
    run_quick,
    run_valuation,
)
from brickvalue.engine.condominium import compute_condominium
from brickvalue.engine.cost import compute_cost
from brickvalue.engine.depreciation import compute_depreciation, ross_coefficient
from brickvalue.engine.income import compute_income
from brickvalue.engine.inference import infer_parameters
from brickvalue.engine.market import compute_market, floor_coefficient
from brickvalue.engine.quick import expand_quick, quick_valuate
from brickvalue.engine.reconciliation import reconcile
from brickvalue.engine.surface import compute_surface
from brickvalue.engine.valuator import valuate

__all__ = [
    "compute_condominium",
    "compute_cost",
    "compute_depreciation",
    "compute_income",
    "compute_market",
    "compute_surface",
    "enrich_request",
    "expand_quick",
    "floor_coefficient",
    "infer_parameters",
    "lookup_address",
    "quick_valuate",
    "reconcile",
    "ross_coefficient",
    "run_quick",
    "run_valuation",
    "valuate",
]
