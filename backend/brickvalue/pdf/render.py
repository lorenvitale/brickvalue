"""Generazione PDF dei report (WeasyPrint).

Il wrapper isola la dipendenza: se WeasyPrint non e' installato, l'API risponde
con 503 invece di fallire all'import.
"""

from __future__ import annotations


def is_available() -> bool:
    """True se WeasyPrint e' importabile."""
    try:
        import weasyprint  # noqa: F401
    except Exception:  # pragma: no cover - dipende dall'ambiente
        return False
    return True


def to_pdf(html: str) -> bytes:
    """Renderizza una stringa HTML in PDF."""
    from weasyprint import HTML

    return HTML(string=html).write_pdf()
