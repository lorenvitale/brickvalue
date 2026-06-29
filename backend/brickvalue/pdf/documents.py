"""Costruzione dell'HTML dei documenti PDF (perizia, condominio, batch)."""

from __future__ import annotations

from datetime import date
from html import escape

from brickvalue.domain.batch import BatchResult
from brickvalue.domain.condominium import CondominiumReport
from brickvalue.domain.results import ValuationReport

# --------------------------------------------------------------------------- #
# Formattazione (locale italiano)
# --------------------------------------------------------------------------- #
def _it(value: float | None, dec: int = 0) -> str:
    if value is None:
        return "—"
    s = f"{value:,.{dec}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def eur(v: float | None) -> str:
    return "—" if v is None else f"€ {_it(v, 0)}"


def eur2(v: float | None) -> str:
    return "—" if v is None else f"€ {_it(v, 2)}"


def num(v: float | None, dec: int = 2) -> str:
    return _it(v, dec)


def pct(v: float | None) -> str:
    return "—" if v is None else f"{_it(v * 100, 2)} %"


def _kv(rows: list[tuple[str, str]]) -> str:
    body = "".join(
        f'<tr><td class="k">{escape(k)}</td><td class="v">{v}</td></tr>' for k, v in rows
    )
    return f'<table class="kv">{body}</table>'


def _section(title: str, inner: str) -> str:
    return f'<section><h2>{escape(title)}</h2>{inner}</section>'


_CSS = """
@page { size: A4; margin: 16mm 15mm 18mm;
  @bottom-center { content: "brickvalue · stima indicativa secondo la prassi estimativa italiana · i valori vanno verificati con dati di mercato reali";
    font-size: 7pt; color: #94a1b5; }
  @bottom-right { content: "pag. " counter(page) "/" counter(pages); font-size: 7.5pt; color: #94a1b5; } }
* { box-sizing: border-box; }
body { font-family: "Helvetica Neue", Arial, sans-serif; color: #15202e; font-size: 10pt; line-height: 1.4; }
.head { display: flex; justify-content: space-between; align-items: flex-end;
  border-bottom: 2.5px solid #c2410c; padding-bottom: 8px; margin-bottom: 14px; }
.head .brand { font-size: 20pt; font-weight: 800; color: #c2410c; letter-spacing: -0.5px; }
.head .brand small { display:block; font-size: 9pt; font-weight: 600; color: #51607a; letter-spacing: 0; }
.head .meta { text-align: right; font-size: 8.5pt; color: #51607a; }
.subtitle { color: #51607a; font-size: 9pt; margin: 0 0 14px; }
.hero { background: #042f2e; color: #fff; border-radius: 8px; padding: 14px 18px; margin-bottom: 16px; }
.hero .lab { font-size: 8.5pt; color: #99f6e4; text-transform: uppercase; letter-spacing: 0.6px; }
.hero .val { font-size: 24pt; font-weight: 800; letter-spacing: -0.5px; }
.cards { display: flex; gap: 10px; margin-bottom: 16px; }
.card { flex: 1; border: 1px solid #e7ebf1; border-radius: 7px; padding: 9px 11px; }
.card .cl { font-size: 7.5pt; color: #94a1b5; text-transform: uppercase; letter-spacing: 0.4px; }
.card .cv { font-size: 13pt; font-weight: 700; }
section { margin-bottom: 13px; }
h2 { font-size: 10.5pt; font-weight: 700; color: #15202e; border-bottom: 1px solid #e7ebf1;
  padding-bottom: 4px; margin: 0 0 7px; }
table { width: 100%; border-collapse: collapse; font-size: 9pt; }
table.data th, table.data td { text-align: left; padding: 4px 7px; border-bottom: 1px solid #eef1f6; }
table.data th { font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.3px; color: #51607a; }
table.data td.num, table.data th.num { text-align: right; }
table.data tr.total td { font-weight: 700; border-top: 1.5px solid #15202e; }
table.kv td { padding: 3px 0; vertical-align: top; }
table.kv td.k { color: #51607a; width: 62%; }
table.kv td.v { text-align: right; font-weight: 600; }
.warn { background: #fffbeb; border-left: 3px solid #b45309; padding: 6px 9px; font-size: 8.5pt;
  color: #78350f; margin: 3px 0; border-radius: 0 4px 4px 0; }
.notes { font-size: 8pt; color: #94a1b5; margin: 4px 0 0; padding-left: 14px; }
"""


def _doc(title: str, body: str) -> str:
    return (
        f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{escape(title)}</title>"
        f"<style>{_CSS}</style></head><body>{body}</body></html>"
    )


def _head(subtitle_kind: str) -> str:
    today = date.today().strftime("%d/%m/%Y")
    return (
        f'<div class="head"><div class="brand">brickvalue'
        f'<small>{escape(subtitle_kind)}</small></div>'
        f'<div class="meta">Documento generato il {today}</div></div>'
    )


# --------------------------------------------------------------------------- #
# Perizia di stima
# --------------------------------------------------------------------------- #
def valuation_html(report: ValuationReport) -> str:
    cs = report.surface.commercial_surface
    addr = None
    if report.geo and report.geo.location:
        loc = report.geo.location
        addr = loc.formatted_address or " ".join(
            x for x in [loc.municipality, f"({loc.province})" if loc.province else None] if x
        )

    body = _head("Perizia di stima immobiliare")
    body += (
        f'<p class="subtitle">Finalità: <b>{escape(report.purpose.value)}</b>'
        f'{" · " + escape(addr) if addr else ""} · '
        f"Superficie commerciale: <b>{num(cs)} m²</b></p>"
    )
    body += (
        f'<div class="hero"><div class="lab">{escape(report.recommended_value_label)}</div>'
        f'<div class="val">{eur(report.recommended_value)}</div></div>'
    )

    cards = [("Valore di mercato", eur(report.market_value), f"{eur2(report.unit_market_value)} /m²")]
    if report.reconstruction_value_new is not None:
        cards.append(("Ricostruzione a nuovo", eur(report.reconstruction_value_new), "assicurativo"))
    cards.append(("Valore cauzionale", eur(report.mortgage_lending_value), "bancario"))
    cards.append(("Pronto realizzo", eur(report.forced_sale_value), "vendita forzata"))
    body += '<div class="cards">' + "".join(
        f'<div class="card"><div class="cl">{escape(l)}</div><div class="cv">{v}</div>'
        f'<div class="cl">{escape(s)}</div></div>'
        for l, v, s in cards
    ) + "</div>"

    # Superficie
    lines = "".join(
        f'<tr><td>{escape(li.label or li.type.value.replace("_", " "))}</td>'
        f'<td class="num">{num(li.area)}</td><td class="num">{num(li.coefficient, 2)}</td>'
        f'<td class="num">{num(li.weighted_area)}</td></tr>'
        for li in report.surface.lines
    )
    body += _section(
        "Superficie commerciale",
        f'<table class="data"><thead><tr><th>Componente</th><th class="num">Area m²</th>'
        f'<th class="num">Coef.</th><th class="num">m² ragg.</th></tr></thead><tbody>{lines}'
        f'<tr class="total"><td>Totale</td><td></td><td></td><td class="num">{num(cs)}</td></tr>'
        f"</tbody></table>",
    )

    # Localizzazione e parametri dedotti
    if report.geo:
        p = report.geo.parameters
        rows = [("Comune", escape(p.city or "—")), ("Regione", escape(p.region or "—"))]
        if p.base_unit_value is not None:
            rows.append(("Valore di zona dedotto", f"{eur2(p.base_unit_value)} /m²"))
        if p.market_rent_sqm_month is not None:
            rows.append(("Canone di mercato stimato", f"{eur2(p.market_rent_sqm_month)} /m²/mese"))
        rows.append(("Affidabilità", escape(p.confidence)))
        body += _section("Localizzazione e parametri dedotti", _kv(rows))

    # Metodi
    if report.market:
        m = report.market
        body += _section("Confronto di mercato", _kv([
            ("Valore unitario base", f"{eur2(m.base_unit_value)} /m²"),
            ("Coefficiente di merito", f"× {num(m.merit_multiplier, 3)}"),
            ("Valore unitario corretto", f"{eur2(m.adjusted_unit_value)} /m²"),
            ("Valore", f"<b>{eur(m.value)}</b>"),
        ]))
    if report.cost:
        c = report.cost
        rows = [
            ("Superficie lorda", f"{num(c.gross_floor_area)} m²"),
            ("Costo di costruzione", f"{eur2(c.construction_cost_per_sqm)} /m²"),
            ("Costo nudo", eur(c.bare_construction_cost)),
            ("Spese tecniche", eur(c.technical_fees)),
            ("Spese generali e utile", eur(c.overhead_profit)),
            ("Ricostruzione a nuovo", f"<b>{eur(c.reconstruction_cost_new)}</b>"),
        ]
        if c.depreciation:
            rows.append(("Deprezzamento (Ross-Heidecke)", pct(c.depreciation.total_depreciation)))
        rows.append(("Valore del suolo", eur(c.land_value)))
        rows.append(("Valore di mercato da costo", f"<b>{eur(c.market_value_via_cost)}</b>"))
        body += _section("Costo / ricostruzione", _kv(rows))
    if report.income:
        i = report.income
        body += _section("Capitalizzazione del reddito", _kv([
            ("Reddito operativo netto", eur(i.net_operating_income)),
            ("Saggio di capitalizzazione", pct(i.cap_rate)),
            ("Valore", f"<b>{eur(i.value)}</b>"),
        ]))

    # Riconciliazione
    rec = report.reconciliation
    rrows = "".join(
        f'<tr><td>{escape(k.replace("_", " "))}</td><td class="num">{pct(rec.weights.get(k))}</td>'
        f'<td class="num">{eur(v)}</td></tr>'
        for k, v in rec.method_values.items()
    )
    body += _section(
        "Riconciliazione",
        f'<table class="data"><thead><tr><th>Metodo</th><th class="num">Peso</th>'
        f'<th class="num">Valore</th></tr></thead><tbody>{rrows}'
        f'<tr class="total"><td>Valore di mercato</td><td></td>'
        f'<td class="num">{eur(rec.market_value)}</td></tr></tbody></table>'
        f'<table class="kv" style="margin-top:6px"><tr><td class="k">Intervallo di valore</td>'
        f'<td class="v">{eur(report.value_range.min)} – {eur(report.value_range.max)}</td></tr></table>',
    )

    if report.warnings:
        body += _section("Avvertenze", "".join(f'<div class="warn">{escape(w)}</div>' for w in report.warnings))
    if report.methodology_notes:
        body += _section("Note metodologiche",
                         '<ul class="notes">' + "".join(f"<li>{escape(n)}</li>" for n in report.methodology_notes) + "</ul>")

    return _doc("Perizia di stima", body)


# --------------------------------------------------------------------------- #
# Condominio
# --------------------------------------------------------------------------- #
def condominium_html(report: CondominiumReport) -> str:
    body = _head("Valore di ricostruzione a nuovo · Condominio")
    body += (
        f'<p class="subtitle">{report.unit_count} unità · {num(report.gross_area)} m² complessivi'
        f'{" · " + escape(report.region) if report.region else ""}</p>'
    )
    body += (
        f'<div class="hero"><div class="lab">Valore di ricostruzione a nuovo (totale)</div>'
        f'<div class="val">{eur(report.reconstruction_value_new)}</div></div>'
    )
    body += _section("Composizione del costo", _kv([
        ("Costo di costruzione (nudo)", eur(report.bare_construction_cost)),
        ("Spese tecniche", eur(report.technical_fees)),
        ("Spese generali e utile", eur(report.overhead_profit)),
        ("Demolizione e sgombero macerie", eur(report.demolition_cost)),
        ("IVA", eur(report.vat)),
        ("Costo al m² (superficie lorda)", f"{eur2(report.value_per_sqm)} /m²"),
        ("Totale ricostruzione a nuovo", f"<b>{eur(report.reconstruction_value_new)}</b>"),
    ]))

    basis = {"millesimi": "millesimi", "superficie": "superficie", "quote_uguali": "quote uguali"}.get(
        report.allocation_basis, report.allocation_basis
    )
    rows = "".join(
        f"<tr><td>{escape(u.label)}</td>"
        f'<td class="num">{num(u.surface_sqm) if u.surface_sqm is not None else "—"}</td>'
        f'<td class="num">{num(u.millesimi, 0) if u.millesimi is not None else "—"}</td>'
        f'<td class="num">{num(u.quota_pct * 100, 2)} %</td>'
        f'<td class="num">{eur(u.insured_value)}</td></tr>'
        for u in report.units
    )
    body += _section(
        f"Somma da assicurare per unità (per {basis})",
        f'<table class="data"><thead><tr><th>Unità</th><th class="num">m²</th><th class="num">‰</th>'
        f'<th class="num">Quota</th><th class="num">Somma assicurata</th></tr></thead><tbody>{rows}'
        f'<tr class="total"><td>Totale</td><td></td><td></td><td></td>'
        f'<td class="num">{eur(report.reconstruction_value_new)}</td></tr></tbody></table>',
    )
    if report.warnings:
        body += _section("Avvertenze", "".join(f'<div class="warn">{escape(w)}</div>' for w in report.warnings))
    return _doc("Ricostruzione condominio", body)


# --------------------------------------------------------------------------- #
# Stima massiva
# --------------------------------------------------------------------------- #
def batch_html(result: BatchResult) -> str:
    body = _head("Stima massiva")
    body += (
        f'<p class="subtitle">{result.count} immobili · {result.ok} valutati'
        f'{(" · " + str(result.errors) + " errori") if result.errors else ""}</p>'
    )
    body += '<div class="cards">' + "".join(
        f'<div class="card"><div class="cl">{escape(l)}</div><div class="cv">{v}</div></div>'
        for l, v in [
            ("Totale valore di mercato", eur(result.total_market_value)),
            ("Totale ricostruzione", eur(result.total_reconstruction_value)),
        ]
    ) + "</div>"

    rows = ""
    for n, it in enumerate(result.items, start=1):
        if it.error:
            rows += (
                f'<tr><td>{n}</td><td>{escape(it.label or it.address or "—")}</td>'
                f'<td colspan="5">⚠ {escape(it.error)}</td></tr>'
            )
            continue
        rows += (
            f"<tr><td>{n}</td><td>{escape(it.label or it.address or '—')}</td>"
            f"<td>{escape(it.city or '—')}</td>"
            f'<td class="num">{num(it.commercial_surface)} m²</td>'
            f'<td class="num">{eur2(it.unit_value)}</td>'
            f'<td class="num">{eur(it.market_value)}</td>'
            f'<td class="num">{eur(it.recommended_value)}</td></tr>'
        )
    body += (
        f'<table class="data"><thead><tr><th>#</th><th>Immobile</th><th>Comune</th>'
        f'<th class="num">Sup.</th><th class="num">€/m²</th><th class="num">Mercato</th>'
        f'<th class="num">Consigliato</th></tr></thead><tbody>{rows}</tbody></table>'
    )
    return _doc("Stima massiva", body)
