"use strict";

/* ============================================================================
 * base.js — Versione semplice (wizard guidato dall'obiettivo).
 * Pochi passi, testo grande, linguaggio non tecnico.
 * ========================================================================== */

const fmtEur = (v) =>
  new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(v || 0);
const esc = (s) =>
  String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const state = {
  goal: null,
  scope: null,
  property_type: "appartamento",
  area_sqm: null,
  num_units: null,
  avg_unit_sqm: 90,
  floor: null,
  total_floors: null,
  address: "",
  year_built: null,
  condition: "buono",
  base_unit_value: null,
};

const STEPS = ["goal", "scope", "size", "details", "result"];
let step = 0;

const wizard = () => document.getElementById("wizard");

/* ----------------------------- componenti UI ----------------------------- */
function optionCard(icon, title, sub, onClick, selected = false) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "opt-card" + (selected ? " selected" : "");
  btn.innerHTML = `<span class="opt-icon">${icon}</span>
    <span class="opt-text"><strong>${esc(title)}</strong><small>${esc(sub)}</small></span>`;
  btn.addEventListener("click", onClick);
  return btn;
}

function navButtons(onNext, nextLabel = "Avanti") {
  const row = document.createElement("div");
  row.className = "wizard-nav";
  if (step > 0) {
    const back = document.createElement("button");
    back.type = "button";
    back.className = "btn-back";
    back.textContent = "← Indietro";
    back.addEventListener("click", () => go(step - 1));
    row.appendChild(back);
  }
  if (onNext) {
    const next = document.createElement("button");
    next.type = "button";
    next.className = "btn-next";
    next.textContent = nextLabel;
    next.addEventListener("click", onNext);
    row.appendChild(next);
  }
  return row;
}

function stepShell(title, subtitle) {
  const root = document.createElement("div");
  root.className = "wizard-step";
  root.innerHTML = `<h2 class="wizard-q">${esc(title)}</h2>` +
    (subtitle ? `<p class="wizard-help">${esc(subtitle)}</p>` : "");
  return root;
}

function bigInput(opts) {
  const wrap = document.createElement("label");
  wrap.className = "big-field";
  wrap.innerHTML = `<span>${esc(opts.label)}</span>`;
  const input = document.createElement("input");
  input.type = opts.type || "number";
  if (opts.min != null) input.min = opts.min;
  if (opts.step != null) input.step = opts.step;
  if (opts.placeholder) input.placeholder = opts.placeholder;
  if (opts.value != null && opts.value !== "") input.value = opts.value;
  if (opts.inputmode) input.inputMode = opts.inputmode;
  input.className = "big-input";
  wrap.appendChild(input);
  if (opts.suffix) {
    const s = document.createElement("span");
    s.className = "field-suffix";
    s.textContent = opts.suffix;
    wrap.appendChild(s);
  }
  wrap._input = input;
  return wrap;
}

function toggleGroup(options, current, onPick) {
  const group = document.createElement("div");
  group.className = "toggle-group";
  options.forEach(([val, label]) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "toggle" + (val === current ? " selected" : "");
    b.textContent = label;
    b.addEventListener("click", () => onPick(val, group));
    group.appendChild(b);
  });
  return group;
}

function setError(node, msg) {
  let e = node.querySelector(".wizard-error");
  if (!e) {
    e = document.createElement("p");
    e.className = "wizard-error";
    node.appendChild(e);
  }
  e.textContent = msg;
}

/* ----------------------------- passi ------------------------------------- */
function renderGoal() {
  const root = stepShell("Cosa ti serve?", "Tocca la risposta giusta per te");
  const cards = document.createElement("div");
  cards.className = "opt-cards";
  cards.appendChild(optionCard("🛡️", "Assicurare la casa",
    "Quanto costa ricostruirla, per la polizza", () => { state.goal = "assicurazione"; go(1); },
    state.goal === "assicurazione"));
  cards.appendChild(optionCard("🏷️", "Sapere quanto vale",
    "Per vendere o per curiosità", () => { state.goal = "vendita"; go(1); },
    state.goal === "vendita"));
  cards.appendChild(optionCard("🏦", "Mutuo o banca",
    "Valore per la banca", () => { state.goal = "mutuo"; go(1); },
    state.goal === "mutuo"));
  root.appendChild(cards);
  return root;
}

function renderScope() {
  const root = stepShell("Che cosa devi valutare?", "");
  const cards = document.createElement("div");
  cards.className = "opt-cards";
  cards.appendChild(optionCard("🏠", "Una casa o un locale",
    "Un singolo appartamento, negozio o ufficio", () => { state.scope = "unita"; go(2); },
    state.scope === "unita"));
  cards.appendChild(optionCard("🏢", "Un intero edificio",
    "Un condominio o palazzo con più unità", () => { state.scope = "edificio"; go(2); },
    state.scope === "edificio"));
  root.appendChild(cards);
  root.appendChild(navButtons(null));
  return root;
}

function renderSize() {
  const isBuilding = state.scope === "edificio";
  const root = stepShell(
    isBuilding ? "Quanto è grande l'edificio?" : "Quanto è grande l'immobile?",
    "Inserisci i dati che conosci"
  );

  let typeField = null;
  let areaField = null;
  let floorField = null;
  let unitsField = null;

  if (!isBuilding) {
    const tWrap = document.createElement("div");
    tWrap.className = "field-block";
    tWrap.innerHTML = `<span class="field-label">Che tipo di immobile è?</span>`;
    typeField = toggleGroup(
      [["appartamento", "Appartamento"], ["villa", "Villa"], ["negozio", "Negozio"], ["ufficio", "Ufficio"]],
      state.property_type,
      (val, group) => {
        state.property_type = val;
        [...group.children].forEach((c) => c.classList.remove("selected"));
        group.querySelector(`button:nth-child(${["appartamento","villa","negozio","ufficio"].indexOf(val)+1})`)?.classList.add("selected");
      }
    );
    tWrap.appendChild(typeField);
    root.appendChild(tWrap);

    areaField = bigInput({ label: "Quanti metri quadri è?", min: 1, step: 1, suffix: "m²",
      inputmode: "numeric", value: state.area_sqm, placeholder: "es. 90" });
    root.appendChild(areaField);

    floorField = bigInput({ label: "A che piano si trova? (facoltativo)", min: -5, step: 1,
      inputmode: "numeric", value: state.floor, placeholder: "0 = piano terra" });
    root.appendChild(floorField);
  } else {
    unitsField = bigInput({ label: "Quante unità (case) ci sono?", min: 1, step: 1,
      inputmode: "numeric", value: state.num_units, placeholder: "es. 12" });
    root.appendChild(unitsField);

    const sizeBlock = document.createElement("div");
    sizeBlock.className = "field-block";
    sizeBlock.innerHTML = `<span class="field-label">Quanto sono grandi in media?</span>`;
    const presets = toggleGroup(
      [["60", "Piccole · 60 m²"], ["90", "Medie · 90 m²"], ["120", "Grandi · 120 m²"]],
      String(state.avg_unit_sqm),
      (val, group) => {
        state.avg_unit_sqm = Number(val);
        [...group.children].forEach((c) => c.classList.toggle("selected", c.textContent.includes(val)));
      }
    );
    sizeBlock.appendChild(presets);
    root.appendChild(sizeBlock);

    floorField = bigInput({ label: "Quanti piani ha l'edificio? (facoltativo)", min: 0, step: 1,
      inputmode: "numeric", value: state.total_floors, placeholder: "es. 4" });
    root.appendChild(floorField);
  }

  const onNext = () => {
    if (!isBuilding) {
      const area = Number(areaField._input.value);
      if (!(area > 0)) return setError(root, "Inserisci i metri quadri (un numero maggiore di zero).");
      state.area_sqm = area;
      const fl = floorField._input.value;
      state.floor = fl === "" ? null : Number(fl);
    } else {
      const units = Number(unitsField._input.value);
      if (!(units > 0)) return setError(root, "Inserisci il numero di unità (un numero maggiore di zero).");
      state.num_units = units;
      const tf = floorField._input.value;
      state.total_floors = tf === "" ? null : Number(tf);
    }
    go(3);
  };
  root.appendChild(navButtons(onNext));
  return root;
}

function renderDetails() {
  const needsPrice = state.goal === "vendita" || state.goal === "mutuo";
  const root = stepShell("Ancora qualche dettaglio", "Se non sai qualcosa, lascia pure vuoto");

  const addrField = bigInput({ label: "Indirizzo (facoltativo)", type: "text",
    value: state.address, placeholder: "Via, civico, comune" });
  root.appendChild(addrField);

  const yearField = bigInput({ label: "Anno di costruzione, circa (facoltativo)", min: 1000, step: 1,
    inputmode: "numeric", value: state.year_built, placeholder: "es. 1990" });
  root.appendChild(yearField);

  const condBlock = document.createElement("div");
  condBlock.className = "field-block";
  condBlock.innerHTML = `<span class="field-label">In che stato è?</span>`;
  const cond = toggleGroup(
    [["come_nuovo", "Come nuovo"], ["buono", "In buono stato"], ["da_sistemare", "Da sistemare"]],
    state.condition,
    (val, group) => {
      state.condition = val;
      [...group.children].forEach((c, i) =>
        c.classList.toggle("selected", ["come_nuovo", "buono", "da_sistemare"][i] === val));
    }
  );
  condBlock.appendChild(cond);
  root.appendChild(condBlock);

  let priceField = null;
  if (needsPrice) {
    priceField = bigInput({ label: "Prezzo medio della zona al m²", min: 1, step: 10, suffix: "€/m²",
      inputmode: "numeric", value: state.base_unit_value, placeholder: "es. 2500" });
    root.appendChild(priceField);
    const help = document.createElement("p");
    help.className = "wizard-help small";
    help.textContent = "Lo trovi guardando gli annunci di case simili nella tua zona.";
    root.appendChild(help);
  }

  const onNext = () => {
    state.address = (addrField._input.value || "").trim();
    const y = yearField._input.value;
    state.year_built = y === "" ? null : Number(y);
    if (needsPrice) {
      const price = Number(priceField._input.value);
      if (!(price > 0)) return setError(root, "Per questo calcolo serve il prezzo medio di zona (€/m²).");
      state.base_unit_value = price;
    }
    go(4);
  };
  root.appendChild(navButtons(onNext, "Calcola →"));
  return root;
}

function buildPayload() {
  const p = { goal: state.goal, scope: state.scope, condition: state.condition };
  if (state.scope === "unita") {
    p.property_type = state.property_type;
    p.area_sqm = state.area_sqm;
    if (state.floor != null && Number.isFinite(state.floor)) p.floor = state.floor;
  } else {
    p.num_units = state.num_units;
    p.avg_unit_sqm = state.avg_unit_sqm;
    if (state.total_floors != null && Number.isFinite(state.total_floors)) p.total_floors = state.total_floors;
  }
  if (state.address) p.address = state.address;
  if (state.year_built != null && Number.isFinite(state.year_built)) p.year_built = state.year_built;
  if (state.base_unit_value != null) p.base_unit_value = state.base_unit_value;
  return p;
}

const GOAL_VIEW = {
  assicurazione: {
    title: "Valore di ricostruzione a nuovo",
    pick: (r) => r.reconstruction_value_new,
    explain: "È la somma da indicare nella <strong>polizza casa</strong>: serve a ricostruire " +
      "l'immobile in caso di danno totale (incendio, crollo…). Non comprende il valore del terreno.",
  },
  vendita: {
    title: "Valore di mercato indicativo",
    pick: (r) => r.market_value,
    explain: "È il prezzo orientativo a cui l'immobile potrebbe essere venduto, in base " +
      "ai dati che hai inserito.",
  },
  mutuo: {
    title: "Valore per la banca (cauzionale)",
    pick: (r) => r.mortgage_lending_value,
    explain: "È il valore prudenziale che una banca considera per concedere un mutuo: " +
      "di norma è inferiore al valore di mercato.",
  },
};

async function renderResult() {
  const root = stepShell("Calcolo in corso…", "");
  root.innerHTML += `<div class="loader"><span class="spinner-lg"></span></div>`;
  wizard().innerHTML = "";
  wizard().appendChild(root);

  let report;
  try {
    const res = await fetch("/api/valuate/quick", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildPayload()),
    });
    report = await res.json();
    if (!res.ok) throw new Error(typeof report.detail === "string" ? report.detail : "Dati non validi");
  } catch (e) {
    const err = stepShell("Qualcosa è andato storto", "");
    const p = document.createElement("p");
    p.className = "wizard-error";
    p.textContent = e.message || "Errore di rete.";
    err.appendChild(p);
    err.appendChild(navButtons(() => go(3), "Riprova"));
    wizard().innerHTML = "";
    wizard().appendChild(err);
    return;
  }

  const view = GOAL_VIEW[state.goal];
  const value = view.pick(report) ?? report.market_value;
  const cs = report.surface.commercial_surface;

  const out = document.createElement("div");
  out.className = "wizard-step result-step";
  out.innerHTML = `
    <div class="result-card">
      <p class="result-label">${esc(view.title)}</p>
      <p class="result-value">${fmtEur(value)}</p>
      <p class="result-explain">${view.explain}</p>
    </div>
    <div class="result-extra">
      <div><span>Superficie considerata</span><strong>${cs.toLocaleString("it-IT")} m²</strong></div>
      ${report.reconstruction_value_new != null ? `<div><span>Ricostruzione a nuovo</span><strong>${fmtEur(report.reconstruction_value_new)}</strong></div>` : ""}
      <div><span>Valore di mercato stimato</span><strong>${fmtEur(report.market_value)}</strong></div>
    </div>
    <p class="wizard-help small">Stima indicativa. Per una perizia ufficiale rivolgiti a un tecnico abilitato.</p>
  `;

  const nav = document.createElement("div");
  nav.className = "wizard-nav result-nav";
  const restart = document.createElement("button");
  restart.type = "button";
  restart.className = "btn-next";
  restart.textContent = "↺ Nuova valutazione";
  restart.addEventListener("click", reset);
  const tech = document.createElement("a");
  tech.href = "/full";
  tech.className = "btn-back";
  tech.textContent = "Dettaglio tecnico";
  nav.appendChild(tech);
  nav.appendChild(restart);
  out.appendChild(nav);

  wizard().innerHTML = "";
  wizard().appendChild(out);
  updateProgress();
}

/* ----------------------------- navigazione ------------------------------- */
function updateProgress() {
  const pct = (step / (STEPS.length - 1)) * 100;
  const bar = document.getElementById("progress-bar");
  if (bar) bar.style.width = pct + "%";
}

function render() {
  updateProgress();
  if (STEPS[step] === "result") return renderResult();
  const map = { goal: renderGoal, scope: renderScope, size: renderSize, details: renderDetails };
  wizard().innerHTML = "";
  wizard().appendChild(map[STEPS[step]]());
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function go(n) {
  step = Math.max(0, Math.min(STEPS.length - 1, n));
  render();
}

function reset() {
  Object.assign(state, {
    goal: null, scope: null, property_type: "appartamento", area_sqm: null,
    num_units: null, avg_unit_sqm: 90, floor: null, total_floors: null,
    address: "", year_built: null, condition: "buono", base_unit_value: null,
  });
  go(0);
}

document.addEventListener("DOMContentLoaded", () => render());
