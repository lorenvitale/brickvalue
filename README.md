# 🧱 brickvalue

**Sistema completo per la valutazione di immobili di qualsiasi tipo**, per uso
**commerciale**, **tecnico**, **bancario** e **assicurativo**.

Calcola il **valore commerciale (di mercato)**, il **valore di ricostruzione a
nuovo** (assicurativo), il **valore cauzionale** (bancario) e il **valore di
pronto realizzo**, secondo la prassi estimativa italiana.

---

## Caratteristiche

- **Superficie commerciale** con ragguaglio delle superfici (balconi, terrazzi,
  cantine, giardini, box, ecc.) tramite coefficienti configurabili.
- **Tre metodi di stima** indipendenti e combinabili:
  - **Confronto di mercato** (Market Comparison Approach) — da valore unitario di
    zona corretto con coefficienti di merito, oppure da immobili comparabili con
    aggiustamenti.
  - **Costo / ricostruzione a nuovo** — costo di costruzione, spese tecniche,
    spese generali e utile, oneri, IVA, demolizione, suolo.
  - **Capitalizzazione del reddito** (Income Approach) — reddito operativo netto
    diviso per il saggio di capitalizzazione.
- **Deprezzamento Ross-Heidecke** (vetustà + stato di manutenzione).
- **Parametri dedotti dall'indirizzo (Google Maps)** — da un indirizzo il sistema
  ricava da solo il valore di zona (€/m²), il saggio di capitalizzazione e il costo
  di costruzione regionale; con le coordinate stima la **centralità** (distanza dal
  centro comune). **Autocompletamento su tutti i ~7.900 comuni italiani** (dataset
  vendorizzato), Google Places quando è configurata la chiave.
- **Condominio (assicuratori)** — valore di ricostruzione a nuovo dell'intero
  fabbricato (parti comuni, demolizione/sgombero macerie, spese tecniche) con
  **ripartizione della somma da assicurare per unità** (millesimi o superficie).
- **Riconciliazione** dei valori con pesi dipendenti dalla finalità della stima.
- **Valori di sintesi**: valore di mercato, ricostruzione a nuovo, cauzionale,
  pronto realizzo, intervallo di valore (min / più probabile / max).
- **Due interfacce web** (responsive, ottimizzate anche per cellulare):
  - **Versione base** — guidata dall'obiettivo (es. valore di ricostruzione per la
    polizza casa), a passi, linguaggio semplice; gestisce *intero fabbricato/
    condominio* (n° unità) e *singola porzione* (mq).
  - **Versione tecnico** — per periti: superficie commerciale, tutti i metodi,
    deprezzamento, report completo, inserimento rapido.
- **API REST** (FastAPI).
- **Validazione robusta** degli input (Pydantic v2) e **suite di test** completa.

---

## Architettura

```
brickvalue/
├── backend/
│   ├── brickvalue/
│   │   ├── domain/        # modelli di dominio (Pydantic): immobile, superfici, input, risultati
│   │   ├── data/          # tabelle e parametri di riferimento (coefficienti, costi, saggi)
│   │   ├── engine/        # motore: superficie, mercato, costo, reddito, deprezzamento, riconciliazione
│   │   ├── api/           # applicazione FastAPI
│   │   └── __main__.py    # entry point CLI (server / demo)
│   └── tests/             # suite pytest
├── frontend/              # interfaccia web statica (HTML/CSS/JS)
├── pyproject.toml
└── requirements.txt
```

Il punto di ingresso del motore è la funzione `brickvalue.valuate(request)`.

---

## Installazione

```bash
pip install -r requirements.txt
```

(opzionale, installazione del package in modalità sviluppo)

```bash
pip install -e ".[test]"
```

---

## Avvio

### Interfaccia web + API

```bash
python -m brickvalue            # http://127.0.0.1:8000
python -m brickvalue --port 9000
```

- Pagina iniziale (scelta versione): <http://127.0.0.1:8000/>
- Versione base (semplice): <http://127.0.0.1:8000/base>
- Versione tecnico (full): <http://127.0.0.1:8000/full>
- Documentazione API (Swagger): <http://127.0.0.1:8000/docs>

### Anteprima offline

```bash
python tools/make_preview.py            # genera ./preview-out/, apri index.html
```

### Valutazione di esempio (CLI)

```bash
python -m brickvalue --demo
```

---

## Uso da codice

```python
from brickvalue import valuate
from brickvalue.domain.enums import PropertyType, ConservationState, ValuationPurpose
from brickvalue.domain.inputs import ValuationRequest, MarketInput, CostInput, IncomeInput
from brickvalue.domain.property import PropertyInput
from brickvalue.domain.surface import SurfaceInput, SurfaceComponent

request = ValuationRequest(
    property=PropertyInput(
        property_type=PropertyType.APARTMENT,
        conservation=ConservationState.GOOD,
        year_built=1995, floor=3, total_floors=5, has_elevator=True,
    ),
    surface=SurfaceInput(components=[
        SurfaceComponent(type="superficie_principale", area=95),
        SurfaceComponent(type="balcone_scoperto", area=12),
        SurfaceComponent(type="cantina_soffitta", area=8),
    ]),
    purpose=ValuationPurpose.MARKET,
    market=MarketInput(base_unit_value=2800),
    cost=CostInput(land_value=60000),
    income=IncomeInput(monthly_rent=1100),
)

report = valuate(request)
print(report.market_value)               # valore di mercato
print(report.reconstruction_value_new)   # valore di ricostruzione a nuovo (assicurativo)
print(report.recommended_value)          # valore consigliato per la finalità
```

---

## API REST

| Metodo | Endpoint         | Descrizione                                  |
|--------|------------------|----------------------------------------------|
| GET    | `/api/health`        | Stato del servizio                           |
| GET    | `/api/reference`     | Tabelle di riferimento (coefficienti, costi) |
| POST   | `/api/surface`       | Calcolo della sola superficie commerciale    |
| POST   | `/api/geocode`       | Indirizzo → localizzazione + parametri dedotti |
| GET    | `/api/geocode/suggest` | Autocompletamento indirizzo (Places + dataset) |
| POST   | `/api/valuate`       | Valutazione completa (versione tecnico)      |
| POST   | `/api/valuate/quick` | Valutazione rapida (versione base)           |
| POST   | `/api/condominio`    | Ricostruzione a nuovo condominio + ripartizione |
| POST   | `/api/valuate/batch` | Stima massiva da elenco di immobili          |

Pagine: `/` (scelta), `/base`, `/condominio`, `/batch`, `/full`. Ogni report
ha il pulsante **Stampa / PDF** (`window.print()` + CSS di stampa).

Il dataset dei comuni è in `backend/brickvalue/data/comuni.json`; per rigenerarlo
(dev): `pip install italy-geopop pyarrow && python tools/gen_comuni.py`.

### Google Maps (parametri automatici)

Imposta la chiave per la geocodifica precisa (coordinate → centralità):

```bash
export GOOGLE_MAPS_API_KEY="la-tua-chiave"
```

Senza chiave il sistema riconosce comunque il comune dall'indirizzo e usa il
dataset di riferimento (`backend/brickvalue/data/market_reference.py`). Quando
una richiesta contiene un indirizzo e non specifica il valore di zona, questo
viene dedotto automaticamente (campo `geo` nel report).

Esempio:

```bash
curl -X POST http://127.0.0.1:8000/api/valuate \
  -H "Content-Type: application/json" \
  -d '{
    "property": {"property_type": "appartamento", "conservation": "buono",
                 "year_built": 2000, "floor": 3, "has_elevator": true},
    "surface": {"components": [{"type": "superficie_principale", "area": 90},
                               {"type": "balcone_scoperto", "area": 8}]},
    "purpose": "commerciale",
    "market": {"base_unit_value": 2500},
    "cost": {"land_value": 40000},
    "income": {"monthly_rent": 950}
  }'
```

---

## Metodologia

### Superficie commerciale
Somma delle superfici reali moltiplicate per i coefficienti di ragguaglio
(es. balcone scoperto 0,30; cantina 0,25; box 0,50), più l'eventuale incidenza
dei muri.

### Deprezzamento (Ross-Heidecke)
```
Dr = ½·(a + a²)              a = età / vita_utile          (vetustà, metodo di Ross)
D  = Dr + C·(1 − Dr)         C = coefficiente di Heidecke  (stato di manutenzione)
valore residuo = (1 − Dr)·(1 − C)
```

### Riconciliazione
Media ponderata dei valori dei metodi disponibili; i pesi dipendono dalla
finalità (es. commerciale → mercato 70%, reddito 20%, costo 10%; assicurativa →
costo 80%, mercato 20%). I pesi sono normalizzati sui metodi effettivamente
calcolati.

### Valori di sintesi per finalità
| Finalità      | Valore consigliato                       |
|---------------|------------------------------------------|
| Commerciale   | Valore di mercato                        |
| Bancario      | Valore cauzionale (prudenziale)          |
| Assicurativo  | Valore di ricostruzione a nuovo          |
| Tecnico       | Valore da costo (deprezzato + suolo)     |
| Legale        | Valore di mercato                        |

---

## Test

```bash
pytest
```

> ⚠️ **Nota.** I valori di riferimento (costi di costruzione, saggi di
> capitalizzazione, coefficienti) sono **indicativi** e pensati come default in
> assenza di dati puntuali. In una perizia reale vanno sostituiti con dati di
> mercato verificati (es. quotazioni OMI di zona, computo metrico). La struttura
> del sistema consente di farlo interamente via input.

---

## Licenza

MIT
