"use strict";

/* ============================================================================
 * condominio.js — Valore di ricostruzione a nuovo del condominio (assicuratori).
 * ========================================================================== */
const $ = (s, r = document) => r.querySelector(s);
const fmtEur = (v) => (v == null ? "—" : new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(v));
const fmtEur2 = (v) => (v == null ? "—" : new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(v));
const fmtNum = (v, d = 2) => (v == null ? "—" : new Intl.NumberFormat("it-IT", { maximumFractionDigits: d }).format(v));
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const STRUCTURES = [
  ["cemento_armato", "Cemento armato"], ["muratura", "Muratura"], ["acciaio", "Acciaio"],
  ["legno", "Legno"], ["mista", "Mista"], ["prefabbricato", "Prefabbricato"],
];

let mode = "detailed";

function addUnitRow(label = "", surface = "", millesimi = "") {
  const row = document.createElement("div");
  row.className = "unit-row";
  row.innerHTML = `
    <input type="text" class="u-label" placeholder="Interno…" value="${esc(label)}" />
    <input type="number" class="u-surface" min="0" step="1" placeholder="m²" value="${surface}" />
    <input type="number" class="u-mill" min="0" step="1" placeholder="‰" value="${millesimi}" />
    <button type="button" class="remove" title="Rimuovi">×</button>`;
  row.querySelector(".remove").addEventListener("click", () => {
    if ($("#unit-rows").children.length > 1) row.remove();
  });
  $("#unit-rows").appendChild(row);
}

function parsePastedUnits(text) {
  const num = (s) => {
    const n = Number(String(s).replace(",", ".").replace(/[^\d.]/g, ""));
    return Number.isFinite(n) && n > 0 ? n : null;
  };
  const units = [];
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    const delim = line.includes("\t") ? "\t" : line.includes(";") ? ";" : ",";
    const cols = line.split(delim).map((c) => c.trim());
    if (cols.length < 2) continue;
    let label = cols[0], mq = num(cols[1]), mill = cols.length >= 3 ? num(cols[2]) : null;
    if (mq == null) {
      // etichetta su più colonne: cerca il primo numero
      for (let i = 1; i < cols.length; i++) {
        const n = num(cols[i]);
        if (n != null) { mq = n; mill = num(cols[i + 1]); label = cols.slice(0, i).join(" "); break; }
      }
    }
    if (mq != null) units.push({ label, mq, mill });
  }
  return units;
}

function importUnits() {
  const msg = $("#paste-msg");
  const units = parsePastedUnits($("#paste-area").value);
  if (!units.length) {
    msg.textContent = "Nessuna riga riconosciuta. Usa: descrizione, mq, millesimi.";
    msg.classList.remove("ok");
    return;
  }
  $("#unit-rows").innerHTML = "";
  units.forEach((u) => addUnitRow(u.label, u.mq, u.mill || ""));
  msg.textContent = `Importate ${units.length} unità.`;
  msg.classList.add("ok");
  $("#paste-area").value = "";
  $("#paste-box").hidden = true;
}

function numOrNull(name) {
  const el = document.querySelector(`[name="${name}"]`);
  if (!el || el.value === "") return null;
  const n = Number(el.value);
  return Number.isFinite(n) ? n : null;
}

function buildRequest() {
  const f = $("#condo-form").elements;
  const req = {
    structure: f.structure.value,
    common_area_sqm: numOrNull("common_area_sqm") || 0,
    technical_fees_pct: (numOrNull("technical_fees_pct") || 0) / 100,
    overhead_profit_pct: (numOrNull("overhead_profit_pct") || 0) / 100,
    demolition_pct: (numOrNull("demolition_pct") || 0) / 100,
    vat_pct: (numOrNull("vat_pct") || 0) / 100,
  };
  const addr = (f.address.value || "").trim();
  if (addr) req.address = addr;
  const y = numOrNull("year_built");
  if (y != null) req.year_built = y;
  const ccs = numOrNull("construction_cost_per_sqm");
  if (ccs != null) req.construction_cost_per_sqm = ccs;

  if (mode === "detailed") {
    req.units = [...$("#unit-rows").children].map((row) => {
      const s = Number(row.querySelector(".u-surface").value);
      const m = row.querySelector(".u-mill").value;
      const u = { surface_sqm: Number.isFinite(s) && s > 0 ? s : null };
      const label = row.querySelector(".u-label").value.trim();
      if (label) u.label = label;
      if (m !== "" && Number(m) > 0) u.millesimi = Number(m);
      return u;
    }).filter((u) => u.surface_sqm);
  } else {
    req.total_area_sqm = numOrNull("total_area_sqm");
    req.num_units = numOrNull("num_units");
  }
  return req;
}

/* ----------------------------- rendering -------------------------------- */
function kv(rows) {
  return `<div class="kv">${rows.map(([k, v]) => `<span class="k">${esc(k)}</span><span class="v">${v}</span>`).join("")}</div>`;
}

function renderReport(r) {
  const pin = window.ICON ? window.ICON("i-pin") : "📍";
  let html = `<div class="report-actions no-print">
    <button type="button" class="btn-secondary" onclick="window.downloadCondoPdf(this)">⭳ Scarica PDF</button>
    <button type="button" class="btn-secondary" onclick="window.print()">Stampa</button></div>
    <h2>Ricostruzione a nuovo del condominio</h2>
    <p class="subtitle">${r.unit_count} unità · ${fmtNum(r.gross_area)} m² complessivi${r.region ? " · " + esc(r.region) : ""}</p>
    <div class="recommended">
      <div class="rec-label">Valore di ricostruzione a nuovo (totale)</div>
      <div class="rec-value">${fmtEur(r.reconstruction_value_new)}</div>
    </div>
    <div class="cards">
      <div class="card primary"><p class="card-label">Costo al m²</p><p class="card-value">${fmtEur2(r.value_per_sqm)}</p><p class="card-sub">su superficie lorda</p></div>
      <div class="card"><p class="card-label">Superficie lorda</p><p class="card-value">${fmtNum(r.gross_area)} m²</p><p class="card-sub">di cui ${fmtNum(r.common_area)} comuni</p></div>
      <div class="card"><p class="card-label">Costo costruzione</p><p class="card-value">${fmtEur2(r.construction_cost_per_sqm)}</p><p class="card-sub">/m²${r.regional_multiplier !== 1 ? " · ×" + fmtNum(r.regional_multiplier, 2) : ""}</p></div>
    </div>`;

  html += `<div class="section"><h3>Composizione del costo</h3>${kv([
    ["Costo di costruzione (nudo)", fmtEur(r.bare_construction_cost)],
    ["Spese tecniche", fmtEur(r.technical_fees)],
    ["Spese generali e utile", fmtEur(r.overhead_profit)],
    ["Demolizione e sgombero macerie", fmtEur(r.demolition_cost)],
    ["IVA", fmtEur(r.vat)],
    ["Totale ricostruzione a nuovo", `<strong>${fmtEur(r.reconstruction_value_new)}</strong>`],
  ])}</div>`;

  const basisLabel = { millesimi: "millesimi", superficie: "superficie", quote_uguali: "quote uguali" }[r.allocation_basis] || r.allocation_basis;
  html += `<div class="section"><h3>Somma da assicurare per unità <small>(per ${esc(basisLabel)})</small></h3>
    <table><thead><tr><th>Unità</th><th class="num">m²</th><th class="num">‰</th><th class="num">Quota</th><th class="num">Somma assicurata</th></tr></thead><tbody>
    ${r.units.map((u) => `<tr>
      <td>${esc(u.label)}</td>
      <td class="num">${u.surface_sqm != null ? fmtNum(u.surface_sqm) : "—"}</td>
      <td class="num">${u.millesimi != null ? fmtNum(u.millesimi, 0) : "—"}</td>
      <td class="num">${fmtNum(u.quota_pct * 100, 2)} %</td>
      <td class="num">${fmtEur(u.insured_value)}</td></tr>`).join("")}
    <tr class="total"><td>Totale</td><td class="num"></td><td class="num"></td><td class="num"></td><td class="num">${fmtEur(r.reconstruction_value_new)}</td></tr>
    </tbody></table></div>`;

  if (r.geo && r.geo.location && r.geo.location.source !== "sconosciuto") {
    const src = r.geo.location.source === "google" ? "Google Maps" : "Dataset comuni";
    html += `<div class="section"><h3>${pin} Localizzazione</h3>${kv([
      ["Comune", esc(r.geo.parameters.city || r.geo.location.municipality || "—")],
      ["Regione", esc(r.region || "—")],
      ["Fonte", esc(src)],
    ])}</div>`;
  }

  if (r.warnings && r.warnings.length) {
    html += `<div class="section"><h3>Avvertenze</h3><ul class="warnings">${r.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}</ul></div>`;
  }
  if (r.notes && r.notes.length) {
    html += `<div class="section"><h3>Note</h3><ul class="notes">${r.notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul></div>`;
  }

  $("#report-content").innerHTML = html;
  $("#report").hidden = false;
  $("#placeholder").hidden = true;
  $("#report").scrollIntoView({ behavior: "smooth", block: "start" });
}

function extractError(data) {
  if (!data) return "risposta non valida";
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) return data.detail.map((d) => `${(d.loc || []).slice(1).join(".")}: ${d.msg}`).join("; ");
  return "richiesta non valida";
}

async function onSubmit(ev) {
  ev.preventDefault();
  const btn = $("#submit-btn");
  const err = $("#form-error");
  err.hidden = true;
  if (mode === "detailed" && ![...$("#unit-rows").children].some((r) => Number(r.querySelector(".u-surface").value) > 0)) {
    err.textContent = "Inserisci almeno un'unità con la superficie.";
    err.hidden = false;
    return;
  }
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Calcolo…';
  try {
    const res = await fetch("/api/condominio", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildRequest()),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(extractError(data));
    renderReport(data);
  } catch (e) {
    err.textContent = "Errore: " + e.message;
    err.hidden = false;
  } finally {
    btn.disabled = false;
    btn.textContent = "Calcola ricostruzione";
  }
}

function setMode(m) {
  mode = m;
  $("#mode-detailed").hidden = m !== "detailed";
  $("#mode-aggregate").hidden = m !== "aggregate";
  document.querySelectorAll(".mode-btn").forEach((b) => b.classList.toggle("selected", b.dataset.mode === m));
}

function loadDemo() {
  const f = $("#condo-form").elements;
  f.address.value = "Via Roma 10, Brescia";
  f.common_area_sqm.value = 120;
  setMode("detailed");
  $("#unit-rows").innerHTML = "";
  addUnitRow("Scala A - Int 1", 85, 180);
  addUnitRow("Scala A - Int 2", 95, 210);
  addUnitRow("Scala A - Int 3", 110, 250);
  addUnitRow("Scala B - Int 4", 75, 160);
  addUnitRow("Scala B - Int 5", 90, 200);
}

async function downloadPdf(url, payload, filename, trigger) {
  const label = trigger ? trigger.textContent : "";
  if (trigger) { trigger.disabled = true; trigger.textContent = "Genero PDF…"; }
  try {
    const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(typeof d.detail === "string" ? d.detail : "PDF non disponibile"); }
    const blob = await res.blob();
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = filename; a.click(); URL.revokeObjectURL(a.href);
  } catch (e) { alert(e.message); } finally { if (trigger) { trigger.disabled = false; trigger.textContent = label; } }
}
window.downloadCondoPdf = (btn) => downloadPdf("/api/condominio/pdf", buildRequest(), "brickvalue-condominio.pdf", btn);

document.addEventListener("DOMContentLoaded", () => {
  $("#structure").innerHTML = STRUCTURES.map(([v, l]) => `<option value="${v}">${l}</option>`).join("");
  addUnitRow();
  $("#condo-form").addEventListener("submit", onSubmit);
  $("#add-unit").addEventListener("click", () => addUnitRow());
  $("#paste-toggle").addEventListener("click", () => { $("#paste-box").hidden = !$("#paste-box").hidden; });
  $("#import-units").addEventListener("click", importUnits);
  $("#demo-btn").addEventListener("click", loadDemo);
  document.querySelectorAll(".mode-btn").forEach((b) => b.addEventListener("click", () => setMode(b.dataset.mode)));
  const addr = document.querySelector('[name="address"]');
  if (addr && window.attachAutocomplete) window.attachAutocomplete(addr, () => {});
});
