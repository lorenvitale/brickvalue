"use strict";

/* ============================ Opzioni (allineate agli enum del backend) ===== */
const OPTIONS = {
  property_type: [
    ["appartamento", "Appartamento"], ["villa", "Villa"],
    ["villetta_a_schiera", "Villetta a schiera"], ["attico", "Attico"],
    ["monolocale", "Monolocale"], ["ufficio", "Ufficio"], ["negozio", "Negozio"],
    ["magazzino", "Magazzino"], ["capannone_industriale", "Capannone industriale"],
    ["struttura_ricettiva", "Struttura ricettiva"], ["box_garage", "Box / Garage"],
    ["posto_auto", "Posto auto"], ["cantina", "Cantina"],
    ["terreno_edificabile", "Terreno edificabile"], ["terreno_agricolo", "Terreno agricolo"],
    ["fabbricato_intero", "Fabbricato intero"],
  ],
  structure: [
    ["cemento_armato", "Cemento armato"], ["muratura", "Muratura"],
    ["acciaio", "Acciaio"], ["legno", "Legno"], ["mista", "Mista"],
    ["prefabbricato", "Prefabbricato"],
  ],
  conservation: [
    ["nuovo", "Nuovo"], ["ottimo", "Ottimo"], ["buono", "Buono"],
    ["normale", "Normale"], ["mediocre", "Mediocre"], ["scadente", "Scadente"],
    ["da_ristrutturare", "Da ristrutturare"], ["inagibile", "Inagibile"],
  ],
  energy_class: [
    ["A4", "A4"], ["A3", "A3"], ["A2", "A2"], ["A1", "A1"], ["B", "B"],
    ["C", "C"], ["D", "D"], ["E", "E"], ["F", "F"], ["G", "G"],
  ],
  purpose: [
    ["commerciale", "Commerciale (valore di mercato)"],
    ["bancario", "Bancario (valore cauzionale)"],
    ["assicurativo", "Assicurativo (ricostruzione a nuovo)"],
    ["tecnico", "Tecnico (costo)"], ["legale", "Legale"],
  ],
  surface: [
    ["superficie_principale", "Superficie principale"],
    ["balcone_coperto", "Balcone coperto"], ["balcone_scoperto", "Balcone scoperto"],
    ["terrazzo", "Terrazzo"], ["veranda", "Veranda"],
    ["giardino_appartamento", "Giardino (appartamento)"],
    ["giardino_villa", "Giardino (villa)"], ["cantina_soffitta", "Cantina / soffitta"],
    ["taverna", "Taverna"], ["box_garage", "Box / Garage"],
    ["posto_auto_coperto", "Posto auto coperto"], ["posto_auto_scoperto", "Posto auto scoperto"],
    ["locale_altezza_ridotta", "Locale altezza ridotta"], ["portico", "Portico"],
  ],
};

/* ============================ Utility ====================================== */
const $ = (sel, root = document) => root.querySelector(sel);
const fmtEur = (v) =>
  v == null ? "—" : new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(v);
const fmtEur2 = (v) =>
  v == null ? "—" : new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(v);
const fmtNum = (v, d = 2) =>
  v == null ? "—" : new Intl.NumberFormat("it-IT", { maximumFractionDigits: d }).format(v);
const fmtPct = (v) => (v == null ? "—" : (v * 100).toFixed(2).replace(".", ",") + " %");
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function fillSelect(id, opts, { placeholder = false } = {}) {
  const el = document.getElementById(id);
  if (!el) return;
  const keep = placeholder ? el.innerHTML : "";
  el.innerHTML = keep + opts.map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join("");
}

/* ============================ Inizializzazione form ======================== */
function initForm() {
  fillSelect("property_type", OPTIONS.property_type);
  fillSelect("structure", OPTIONS.structure);
  fillSelect("conservation", OPTIONS.conservation);
  fillSelect("energy_class", OPTIONS.energy_class, { placeholder: true });
  fillSelect("purpose", OPTIONS.purpose);
  $("#conservation").value = "buono";
  addSurfaceRow("superficie_principale", "");
}

function surfaceOptionsHtml(selected) {
  return OPTIONS.surface
    .map(([v, l]) => `<option value="${v}" ${v === selected ? "selected" : ""}>${esc(l)}</option>`)
    .join("");
}

function addSurfaceRow(type = "superficie_principale", area = "") {
  const row = document.createElement("div");
  row.className = "surface-row";
  row.innerHTML = `
    <label>Tipo<select class="s-type">${surfaceOptionsHtml(type)}</select></label>
    <label>Area m²<input type="number" class="s-area" min="0" step="0.1" value="${area}" /></label>
    <label>Coef.<input type="number" class="s-coef" min="0" max="2" step="0.05" placeholder="auto" /></label>
    <button type="button" class="remove" title="Rimuovi">×</button>`;
  row.querySelector(".remove").addEventListener("click", () => {
    if ($("#surface-rows").children.length > 1) row.remove();
  });
  $("#surface-rows").appendChild(row);
}

/* ============================ Costruzione richiesta ======================== */
function numOrNull(name) {
  const el = document.querySelector(`[name="${name}"]`);
  if (!el || el.value === "") return null;
  const n = Number(el.value);
  return Number.isFinite(n) ? n : null;
}

function buildRequest() {
  const form = $("#valuation-form");
  const get = (n) => form.elements[n];

  // Superfici
  const components = [...$("#surface-rows").children].map((row) => {
    const area = Number(row.querySelector(".s-area").value);
    const coefRaw = row.querySelector(".s-coef").value;
    const c = { type: row.querySelector(".s-type").value, area: Number.isFinite(area) ? area : 0 };
    if (coefRaw !== "") c.coefficient = Number(coefRaw);
    return c;
  }).filter((c) => c.area > 0);

  const property = {
    property_type: get("property_type").value,
    structure: get("structure").value,
    conservation: get("conservation").value,
    has_elevator: get("has_elevator").checked,
    is_penthouse: get("is_penthouse").checked,
  };
  if (get("energy_class").value) property.energy_class = get("energy_class").value;
  for (const f of ["year_built", "year_renovated", "floor", "total_floors"]) {
    const v = numOrNull(f);
    if (v != null) property[f] = v;
  }

  const req = {
    property,
    surface: { components, wall_incidence_pct: (numOrNull("wall_incidence_pct") || 0) / 100 },
    purpose: get("purpose").value,
  };

  const baseUnit = numOrNull("base_unit_value");
  if (baseUnit != null) req.market = { base_unit_value: baseUnit };

  const cost = {};
  for (const [field, key] of [["gross_floor_area", "gross_floor_area"],
                              ["construction_cost_per_sqm", "construction_cost_per_sqm"],
                              ["land_value", "land_value"]]) {
    const v = numOrNull(field);
    if (v != null) cost[key] = v;
  }
  const vat = numOrNull("vat_pct");
  if (vat != null) cost.vat_pct = vat / 100;
  if (Object.keys(cost).length) req.cost = cost;

  const rent = numOrNull("monthly_rent");
  if (rent != null) {
    req.income = { monthly_rent: rent };
    const cap = numOrNull("cap_rate");
    if (cap != null) req.income.cap_rate = cap / 100;
  }

  return req;
}

/* ============================ Rendering report ============================= */
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

  // Valore consigliato
  html += `<div class="recommended">
      <div class="rec-label">${esc(r.recommended_value_label)}</div>
      <div class="rec-value">${fmtEur(r.recommended_value)}</div>
    </div>`;

  // Cards
  html += `<div class="cards">
    ${card("Valore di mercato", fmtEur(r.market_value), `${fmtEur2(r.unit_market_value)} /m²`, true)}
    ${r.reconstruction_value_new != null ? card("Ricostruzione a nuovo", fmtEur(r.reconstruction_value_new), "assicurativo") : ""}
    ${card("Valore cauzionale", fmtEur(r.mortgage_lending_value), "bancario")}
    ${card("Pronto realizzo", fmtEur(r.forced_sale_value), "vendita forzata")}
  </div>`;

  // Range
  html += renderRange(r.value_range, r.market_value);

  // Superficie
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

  // Metodi
  if (r.market) html += renderMarket(r.market);
  if (r.cost) html += renderCost(r.cost);
  if (r.income) html += renderIncome(r.income);

  // Riconciliazione
  html += renderReconciliation(r.reconciliation);

  // Warnings
  if (r.warnings && r.warnings.length) {
    html += `<div class="section"><h3>Avvertenze</h3>
      <ul class="warnings">${r.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}</ul></div>`;
  }

  // Note metodologiche
  if (r.methodology_notes && r.methodology_notes.length) {
    html += `<div class="section"><h3>Note metodologiche</h3>
      <ul class="notes">${r.methodology_notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul></div>`;
  }

  $("#report-content").innerHTML = html;
  $("#report").hidden = false;
  $("#placeholder").hidden = true;
  $("#report").scrollIntoView({ behavior: "smooth", block: "start" });
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

/* ============================ Submit / Demo =============================== */
async function onSubmit(ev) {
  ev.preventDefault();
  const btn = $("#submit-btn");
  const errEl = $("#form-error");
  errEl.hidden = true;
  const rows = [...$("#surface-rows").children];
  if (!rows.some((r) => Number(r.querySelector(".s-area").value) > 0)) {
    errEl.textContent = "Inserire almeno una superficie con area maggiore di zero.";
    errEl.hidden = false;
    return;
  }
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Calcolo…';
  try {
    const res = await fetch("/api/valuate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildRequest()),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(extractError(data));
    }
    renderReport(data);
  } catch (e) {
    errEl.textContent = "Errore: " + e.message;
    errEl.hidden = false;
  } finally {
    btn.disabled = false;
    btn.textContent = "Calcola valutazione";
  }
}

function extractError(data) {
  if (!data) return "risposta non valida";
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map((d) => `${(d.loc || []).slice(1).join(".")}: ${d.msg}`).join("; ");
  }
  return "richiesta non valida";
}

function loadDemo() {
  const f = $("#valuation-form").elements;
  f.property_type.value = "appartamento";
  f.structure.value = "cemento_armato";
  f.conservation.value = "buono";
  f.energy_class.value = "C";
  f.year_built.value = 1995;
  f.floor.value = 3;
  f.total_floors.value = 5;
  f.has_elevator.checked = true;
  f.purpose.value = "commerciale";
  f.base_unit_value.value = 2800;
  f.land_value.value = 60000;
  f.monthly_rent.value = 1100;
  $("#surface-rows").innerHTML = "";
  addSurfaceRow("superficie_principale", 95);
  addSurfaceRow("balcone_scoperto", 12);
  addSurfaceRow("cantina_soffitta", 8);
}

/* ============================ Avvio ====================================== */
document.addEventListener("DOMContentLoaded", () => {
  initForm();
  $("#valuation-form").addEventListener("submit", onSubmit);
  $("#add-surface").addEventListener("click", () => addSurfaceRow());
  $("#demo-btn").addEventListener("click", loadDemo);
});
