"use strict";

/* ============================================================================
 * app.js — Logica dell'interfaccia: form, costruzione richiesta, chiamata API.
 * Le funzioni di formattazione e rendering del report sono in render.js
 * (caricato prima di questo file).
 * ========================================================================== */

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

/* ============================ Inizializzazione form ======================== */
function fillSelect(id, opts, { placeholder = false } = {}) {
  const el = document.getElementById(id);
  if (!el) return;
  const keep = placeholder ? el.innerHTML : "";
  el.innerHTML = keep + opts.map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join("");
}

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

function mainSurfaceArea() {
  return [...$("#surface-rows").children].reduce((sum, row) => {
    if (row.querySelector(".s-type").value === "superficie_principale") {
      const a = Number(row.querySelector(".s-area").value);
      if (Number.isFinite(a)) sum += a;
    }
    return sum;
  }, 0);
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

  // Ubicazione (opzionale)
  const location = {};
  for (const field of ["address", "municipality", "cadastral_ref"]) {
    const el = form.elements[field];
    if (el && el.value && el.value.trim()) location[field] = el.value.trim();
  }
  if (Object.keys(location).length) property.location = location;

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

let lastDetectedAddress = "";

async function detectZone() {
  const form = $("#valuation-form");
  const note = $("#zone-note");
  const address = (form.elements["address"].value || "").trim();
  if (!address) {
    note.hidden = false;
    note.textContent = "Inserisci prima l'indirizzo completo.";
    return;
  }
  const btn = $("#detect-zone");
  btn.disabled = true;
  note.hidden = false;
  note.textContent = "Ricerca in corso…";
  try {
    const res = await fetch("/api/geocode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address, property_type: form.elements["property_type"].value }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(extractError(data));
    const p = data.parameters;
    if (p.base_unit_value != null) form.elements["base_unit_value"].value = p.base_unit_value;

    // Automazione: precompila il canone stimato (così parte anche il metodo reddituale)
    const mainArea = mainSurfaceArea();
    let rentMsg = "";
    if (p.market_rent_sqm_month != null && mainArea > 0) {
      const rentField = form.elements["monthly_rent"];
      const estTotal = Math.round(p.market_rent_sqm_month * mainArea);
      if (rentField && rentField.value === "") {
        rentField.value = estTotal;
        rentMsg = ` · canone stimato ${fmtEur(estTotal)}/mese`;
      }
    }
    const where = p.city || data.location.municipality || data.location.formatted_address || address;
    note.classList.add("ok");
    note.textContent = `${where}${p.region ? " (" + p.region + ")" : ""} · ~${fmtEur2(p.base_unit_value)}/m² · affidabilità ${p.confidence}${rentMsg}`;
    lastDetectedAddress = address;
  } catch (e) {
    note.textContent = "Non è stato possibile dedurre il valore: " + e.message;
  } finally {
    btn.disabled = false;
  }
}

/* ============================ Avvio ====================================== */
document.addEventListener("DOMContentLoaded", () => {
  initForm();
  $("#valuation-form").addEventListener("submit", onSubmit);
  $("#add-surface").addEventListener("click", () => addSurfaceRow());
  $("#demo-btn").addEventListener("click", loadDemo);
  $("#detect-zone").addEventListener("click", detectZone);
  const addr = document.querySelector('[name="address"]');
  if (addr) {
    // Auto-rilevamento: alla scelta di un suggerimento o uscendo dal campo
    if (window.attachAutocomplete) window.attachAutocomplete(addr, () => detectZone());
    addr.addEventListener("change", () => {
      const v = addr.value.trim();
      if (v && v !== lastDetectedAddress) detectZone();
    });
  }
});
