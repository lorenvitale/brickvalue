"""brickvalue — Sistema completo per la valutazione di immobili.

Il package espone:

* :mod:`brickvalue.domain`   — modelli di dominio (immobile, superfici, risultati)
* :mod:`brickvalue.engine`   — motore di calcolo (metodi di stima)
* :mod:`brickvalue.data`     — dati di riferimento (costi, coefficienti, saggi)
* :mod:`brickvalue.api`      — API REST (FastAPI)

L'entry point ad alto livello è :func:`brickvalue.engine.valuator.valuate`.
"""

from __future__ import annotations

__version__ = "1.0.0"

from brickvalue.engine.valuator import valuate

__all__ = ["valuate", "__version__"]
