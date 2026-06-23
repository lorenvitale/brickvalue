"use strict";

/* ============================================================================
 * render.js — Funzioni di formattazione e rendering del report.
 * Condiviso tra l'app interattiva (app.js) e l'anteprima statica (preview).
 * Espone funzioni nello scope globale (nessun modulo, caricato per primo).
 * ========================================================================== */

const $ = (sel, root = document) => root.querySelector(sel);

const fmtEur = (v) =>
  v == null ? "—" : new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(v);
const fmtEur2 = (v) =>
  v == null ? "—" : new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(v);
const fmtNum = (v, d = 2) =>
  v == null ? "—" : new Intl.NumberFormat("it-IT", { maximumFractionDigits: d }).format(v);
const fmtPct = (v) => (v == null ? "—" : (v * 100).toFixed(2).replace(".", ",") + " %");
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function methodLabel(key) {
  return {
    confronto_di_mercato: "Confronto di mercato",
    costo_di_ricostruzione: "Costo / ricostruzione",
    capitalizzazione_reddito: "Capitalizzazione del reddito",
  }[key] || key;
}

function renderReport(r) {
  const cs = r.surface.commercial_surface;
  let html = "";

  html += `<h2>Report di valutazione</h2>
    <p class="subtitle">Finalità: <strong>${esc(r.purpose)}</strong> · Superficie commerciale: <strong>${fmtNum(cs)} m²</strong></p>`;

  html += `<div class="recommended">
      <div class="rec-label">${esc(r.recommended_value_label)}</div>
      <div class="rec-value">${fmtEur(r.recommended_value)}</div>
    </div>`;

  html += `<div class="cards">
    ${card("Valore di mercato", fmtEur(r.market_value), `${fmtEur2(r.unit_market_value)} /m²`, true)}
    ${r.reconstruction_value_new != null ? card("Ricostruzione a nuovo", fmtEur(r.reconstruction_value_new), "assicurativo") : ""}
    ${card("Valore cauzionale", fmtEur(r.mortgage_lending_value), "bancario")}
    ${card("Pronto realizzo", fmtEur(r.forced_sale_value), "vendita forzata")}
  </div>`;

  html += renderRange(r.value_range, r.market_value);

  if (r.geo) html += renderGeo(r.geo);

  html += `<div class="section"><h3>Superficie commerciale</h3>
    <table><thead><tr><th>Componente</th><th class="num">Area m²</th><th class="num">Coef.</th><th class="num">m² ragguagliati</th></tr></thead><tbody>
    ${r.surface.lines.map((l) => `<tr>
      <td>${esc(l.label || l.type.replace(/_/g, " "))}</td>
      <td class="num">${fmtNum(l.area)}</td>
      <td class="num">${fmtNum(l.coefficient, 2)}</td>
      <td class="num">${fmtNum(l.weighted_area)}</td></tr>`).join("")}
    ${r.surface.wall_area_added > 0 ? `<tr><td>Incidenza muri (${(r.surface.wall_incidence_pct * 100).toFixed(0)}%)</td><td class="num">—</td><td class="num">—</td><td class="num">${fmtNum(r.surface.wall_area_added)}</td></tr>` : ""}
    <tr class="total"><td>Totale</td><td class="num"></td><td class="num"></td><td class="num">${fmtNum(cs)}</td></tr>
    </tbody></table></div>`;

  if (r.market) html += renderMarket(r.market);
  if (r.cost) html += renderCost(r.cost);
  if (r.income) html += renderIncome(r.income);

  html += renderReconciliation(r.reconciliation);

  if (r.warnings && r.warnings.length) {
    html += `<div class="section"><h3>Avvertenze</h3>
      <ul class="warnings">${r.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}</ul></div>`;
  }
  if (r.methodology_notes && r.methodology_notes.length) {
    html += `<div class="section"><h3>Note metodologiche</h3>
      <ul class="notes">${r.methodology_notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul></div>`;
  }

  $("#report-content").innerHTML = html;
  const report = $("#report");
  const placeholder = $("#placeholder");
  if (report) report.hidden = false;
  if (placeholder) placeholder.hidden = true;
  if (report && report.scrollIntoView) report.scrollIntoView({ behavior: "smooth", block: "start" });
}

function card(label, value, sub, primary = false) {
  return `<div class="card ${primary ? "primary" : ""}">
    <p class="card-label">${esc(label)}</p>
    <p class="card-value">${value}</p>
    ${sub ? `<p class="card-sub">${esc(sub)}</p>` : ""}</div>`;
}

function renderRange(range, mid) {
  const span = range.max - range.min || 1;
  const pos = ((mid - range.min) / span) * 100;
  return `<div class="section"><h3>Intervallo di valore</h3>
    <div class="range-bar"><div class="range-fill" style="left:0;width:100%"></div>
      <div class="range-mid" style="left:${pos}%"></div></div>
    <div class="range-labels"><span>${fmtEur(range.min)}</span>
      <span><strong>${fmtEur(range.most_likely)}</strong></span>
      <span>${fmtEur(range.max)}</span></div></div>`;
}

function kv(rows) {
  return `<div class="kv">${rows.map(([k, v]) => `<span class="k">${esc(k)}</span><span class="v">${v}</span>`).join("")}</div>`;
}

function renderGeo(g) {
  const loc = g.location, p = g.parameters;
  const src = loc.source === "google" ? "Google Maps"
    : loc.source === "fallback_testuale" ? "Dataset di riferimento" : "Non riconosciuta";
  const place = loc.formatted_address ||
    [loc.municipality, loc.province].filter(Boolean).join(" ") || "—";
  const rows = [["Fonte", esc(src)], ["Località", esc(place)]];
  if (p.region) rows.push(["Regione", esc(p.region)]);
  if (p.distance_to_center_km != null) rows.push(["Distanza dal centro", `${fmtNum(p.distance_to_center_km)} km`]);
  if (p.centrality_multiplier != null) rows.push(["Centralità", `×${fmtNum(p.centrality_multiplier, 2)}`]);
  if (p.base_unit_value != null) rows.push(["Valore di zona dedotto", `${fmtEur2(p.base_unit_value)} /m²`]);
  if (p.cap_rate != null) rows.push(["Saggio dedotto", fmtPct(p.cap_rate)]);
  rows.push(["Affidabilità", esc(p.confidence)]);
  return `<div class="section"><h3>📍 Localizzazione e parametri dedotti</h3>${kv(rows)}
    ${p.notes && p.notes.length ? `<p class="notes">${p.notes.map(esc).join(" · ")}</p>` : ""}</div>`;
}

function renderMarket(m) {
  let breakdown = Object.entries(m.merit_breakdown || {})
    .map(([k, v]) => `${esc(k)}: ×${fmtNum(v, 2)}`).join(" · ");
  let extra = "";
  if (m.approach === "comparables" && m.comparables_detail.length) {
    extra = `<table><thead><tr><th>Comparabile</th><th class="num">Prezzo</th><th class="num">€/m²</th><th class="num">Agg.</th><th class="num">€/m² agg.</th></tr></thead><tbody>
      ${m.comparables_detail.map((c) => `<tr><td>${esc(c.label || "—")}</td>
        <td class="num">${fmtEur(c.price)}</td><td class="num">${fmtEur(c.unit_price)}</td>
        <td class="num">${fmtPct(c.net_adjustment)}</td><td class="num">${fmtEur(c.adjusted_unit_price)}</td></tr>`).join("")}</tbody></table>`;
  }
  return `<div class="section"><h3>Confronto di mercato</h3>
    ${kv([
      ["Approccio", esc(m.approach)],
      ["Valore unitario base", `${fmtEur2(m.base_unit_value)} /m²`],
      ["Coefficiente di merito", `×${fmtNum(m.merit_multiplier, 3)}`],
      ["Valore unitario corretto", `${fmtEur2(m.adjusted_unit_value)} /m²`],
      ["Valore", `<strong>${fmtEur(m.value)}</strong>`],
    ])}
    ${breakdown ? `<p class="notes">${breakdown}</p>` : ""}
    ${extra}</div>`;
}

function renderCost(c) {
  let dep = "";
  if (c.depreciation) {
    const d = c.depreciation;
    dep = kv([
      ["Età / vita utile", `${d.age_years} / ${d.useful_life_years} anni`],
      ["Coeff. Ross (vetustà)", fmtPct(d.ross_coefficient)],
      ["Coeff. Heidecke (stato)", fmtPct(d.heidecke_coefficient)],
      ["Deprezzamento totale", fmtPct(d.total_depreciation)],
      ["Valore residuo", fmtPct(d.residual_ratio)],
    ]);
  }
  return `<div class="section"><h3>Costo / ricostruzione</h3>
    ${kv([
      ["Superficie lorda", `${fmtNum(c.gross_floor_area)} m²`],
      ["Costo costruzione", `${fmtEur2(c.construction_cost_per_sqm)} /m²`],
      ["Costo nudo", fmtEur(c.bare_construction_cost)],
      ["Spese tecniche", fmtEur(c.technical_fees)],
      ["Spese generali e utile", fmtEur(c.overhead_profit)],
      ["IVA", fmtEur(c.vat)],
      ["Ricostruzione a nuovo", `<strong>${fmtEur(c.reconstruction_cost_new)}</strong>`],
      ["Valore del suolo", fmtEur(c.land_value)],
      ["Valore di mercato da costo", `<strong>${fmtEur(c.market_value_via_cost)}</strong>`],
    ])}
    ${dep ? `<h3 style="margin-top:14px">Deprezzamento (Ross-Heidecke)</h3>${dep}` : ""}</div>`;
}

function renderIncome(i) {
  return `<div class="section"><h3>Capitalizzazione del reddito</h3>
    ${kv([
      ["Reddito lordo potenziale", fmtEur(i.potential_gross_income)],
      ["Reddito effettivo", fmtEur(i.effective_gross_income)],
      ["Spese di gestione", fmtEur(i.operating_expenses)],
      ["Reddito operativo netto", fmtEur(i.net_operating_income)],
      ["Saggio di capitalizzazione", fmtPct(i.cap_rate)],
      ["Rendimento lordo", fmtPct(i.gross_yield)],
      ["Valore", `<strong>${fmtEur(i.value)}</strong>`],
    ])}</div>`;
}

function renderReconciliation(rec) {
  return `<div class="section"><h3>Riconciliazione</h3>
    <table><thead><tr><th>Metodo</th><th class="num">Peso</th><th class="num">Valore</th></tr></thead><tbody>
    ${Object.keys(rec.method_values).map((k) => `<tr><td>${esc(methodLabel(k))}</td>
      <td class="num">${fmtPct(rec.weights[k])}</td><td class="num">${fmtEur(rec.method_values[k])}</td></tr>`).join("")}
    <tr class="total"><td>Valore di mercato</td><td class="num"></td><td class="num">${fmtEur(rec.market_value)}</td></tr>
    </tbody></table></div>`;
}
