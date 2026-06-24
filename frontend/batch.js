"use strict";

/* ============================================================================
 * batch.js — Stima massiva: incolla un elenco, ottieni una tabella + CSV.
 * ========================================================================== */
const $ = (s, r = document) => r.querySelector(s);
const fmtEur = (v) => (v == null ? "—" : new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(v));
const fmtEur2 = (v) => (v == null ? "—" : new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(v));
const fmtNum = (v, d = 0) => (v == null ? "—" : new Intl.NumberFormat("it-IT", { maximumFractionDigits: d }).format(v));
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const TYPE_ALIASES = {
  appartamento: "appartamento", appartamenti: "appartamento", casa: "appartamento", abitazione: "appartamento",
  villa: "villa", villetta: "villetta_a_schiera", schiera: "villetta_a_schiera", attico: "attico",
  monolocale: "monolocale", ufficio: "ufficio", uffici: "ufficio", negozio: "negozio", negozi: "negozio",
  magazzino: "magazzino", capannone: "capannone_industriale", industriale: "capannone_industriale",
  box: "box_garage", garage: "box_garage", "posto auto": "posto_auto", cantina: "cantina",
  terreno: "terreno_edificabile", edificabile: "terreno_edificabile", agricolo: "terreno_agricolo",
  fabbricato: "fabbricato_intero", condominio: "fabbricato_intero", hotel: "struttura_ricettiva",
};
const PURPOSE_ALIASES = {
  commerciale: "commerciale", vendita: "commerciale", mercato: "commerciale",
  assicurativo: "assicurativo", assicurazione: "assicurativo", polizza: "assicurativo",
  bancario: "bancario", mutuo: "bancario", banca: "bancario", tecnico: "tecnico", legale: "legale",
};

let lastResult = null;

function num(s) {
  const n = Number(String(s).replace(",", ".").replace(/[^\d.]/g, ""));
  return Number.isFinite(n) && n > 0 ? n : null;
}

function mapAlias(value, table, fallback) {
  const v = String(value || "").trim().toLowerCase();
  if (!v) return fallback;
  if (table[v]) return table[v];
  for (const key in table) if (v.includes(key)) return table[key];
  return fallback;
}

function parseLines(text) {
  const items = [];
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    const delim = line.includes("\t") ? "\t" : line.includes(";") ? ";" : ",";
    const cols = line.split(delim).map((c) => c.trim());
    if (cols.length < 2) continue;
    const area = num(cols[1]);
    if (area == null) continue; // salta intestazioni o righe senza mq
    items.push({
      label: cols[0] || null,
      address: cols[0] || null,
      area_sqm: area,
      property_type: mapAlias(cols[2], TYPE_ALIASES, "appartamento"),
      purpose: mapAlias(cols[3], PURPOSE_ALIASES, "commerciale"),
    });
  }
  return items;
}

function renderResults(res) {
  const rows = res.items.map((it, i) => {
    if (it.error) {
      return `<tr class="row-error"><td>${i + 1}</td><td>${esc(it.label || it.address || "—")}</td>
        <td colspan="6">⚠ ${esc(it.error)}</td></tr>`;
    }
    return `<tr>
      <td>${i + 1}</td>
      <td>${esc(it.label || it.address || "—")}</td>
      <td>${esc(it.city || "—")}</td>
      <td class="num">${fmtNum(it.commercial_surface)} m²</td>
      <td class="num">${fmtEur2(it.unit_value)}</td>
      <td class="num">${fmtEur(it.market_value)}</td>
      <td class="num">${fmtEur(it.reconstruction_value_new)}</td>
      <td class="num"><strong>${fmtEur(it.recommended_value)}</strong></td>
    </tr>`;
  }).join("");

  $("#batch-results").innerHTML = `
    <div class="batch-summary">
      <div class="bs"><span>Immobili</span><strong>${res.count}</strong></div>
      <div class="bs"><span>Valutati</span><strong>${res.ok}</strong></div>
      ${res.errors ? `<div class="bs err"><span>Errori</span><strong>${res.errors}</strong></div>` : ""}
      <div class="bs"><span>Totale valore di mercato</span><strong>${fmtEur(res.total_market_value)}</strong></div>
      <div class="bs"><span>Totale ricostruzione</span><strong>${fmtEur(res.total_reconstruction_value)}</strong></div>
    </div>
    <div class="table-scroll"><table><thead><tr>
      <th>#</th><th>Immobile</th><th>Comune</th><th class="num">Sup.</th><th class="num">€/m²</th>
      <th class="num">Mercato</th><th class="num">Ricostruzione</th><th class="num">Consigliato</th>
    </tr></thead><tbody>${rows}</tbody></table></div>`;
  $("#batch-results").hidden = false;
  $("#csv-btn").hidden = false;
  $("#print-btn").hidden = false;
}

function toCSV(res) {
  const head = ["Immobile", "Comune", "Regione", "Finalita", "Superficie_mq", "Valore_mq", "Valore_mercato", "Ricostruzione_a_nuovo", "Consigliato", "Affidabilita", "Errore"];
  const rows = res.items.map((it) => [
    it.label || it.address || "", it.city || "", it.region || "", it.purpose || "",
    it.commercial_surface ?? "", it.unit_value ?? "", it.market_value ?? "",
    it.reconstruction_value_new ?? "", it.recommended_value ?? "", it.confidence || "", it.error || "",
  ]);
  const escCsv = (v) => {
    const s = String(v);
    return /[",;\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  return [head, ...rows].map((r) => r.map(escCsv).join(";")).join("\r\n");
}

function downloadCSV() {
  if (!lastResult) return;
  const blob = new Blob(["﻿" + toCSV(lastResult)], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "brickvalue-stima-massiva.csv";
  a.click();
  URL.revokeObjectURL(a.href);
}

async function run() {
  const err = $("#batch-error");
  err.hidden = true;
  const items = parseLines($("#batch-area").value);
  if (!items.length) {
    err.textContent = "Nessuna riga valida. Formato: indirizzo; mq; tipo; finalità.";
    err.hidden = false;
    return;
  }
  const btn = $("#run-btn");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Valutazione…';
  try {
    const res = await fetch("/api/valuate/batch", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "richiesta non valida");
    lastResult = data;
    renderResults(data);
  } catch (e) {
    err.textContent = "Errore: " + e.message;
    err.hidden = false;
  } finally {
    btn.disabled = false;
    btn.textContent = "Valuta elenco";
  }
}

function loadDemo() {
  $("#batch-area").value =
    "Via Dante 1, Milano\t95\tappartamento\tcommerciale\n" +
    "Corso Italia 5, Napoli\t120\tufficio\tcommerciale\n" +
    "Desenzano del Garda\t85\tappartamento\tassicurativo\n" +
    "Via Po, Torino\t70\tappartamento\tbancario\n" +
    "Lecce centro\t110\tnegozio\tcommerciale";
}

document.addEventListener("DOMContentLoaded", () => {
  $("#run-btn").addEventListener("click", run);
  $("#demo-btn").addEventListener("click", loadDemo);
  $("#csv-btn").addEventListener("click", downloadCSV);
  $("#print-btn").addEventListener("click", () => window.print());
});
