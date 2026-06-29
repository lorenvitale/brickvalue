"""Generazione PDF dei report."""

from __future__ import annotations

from brickvalue.pdf.documents import batch_html, condominium_html, valuation_html
from brickvalue.pdf.render import is_available, to_pdf

__all__ = [
    "batch_html",
    "condominium_html",
    "is_available",
    "to_pdf",
    "valuation_html",
]
