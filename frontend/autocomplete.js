"use strict";

/* ============================================================================
 * autocomplete.js — Autocompletamento indirizzi (Google Places via backend,
 * fallback dataset comuni). Esposto come window.attachAutocomplete.
 * IIFE per non collidere con gli helper globali di render.js/app.js.
 * ========================================================================== */
(function () {
  const esc = (s) =>
    String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function attachAutocomplete(input, onSelect) {
    if (!input || input._acAttached) return;
    input._acAttached = true;

    const box = document.createElement("div");
    box.className = "ac-box";
    input.parentNode.insertBefore(box, input);
    box.appendChild(input);

    const list = document.createElement("ul");
    list.className = "ac-list";
    list.hidden = true;
    box.appendChild(list);

    let items = [];
    let active = -1;
    let timer = null;
    let lastQuery = null;

    const close = () => {
      list.hidden = true;
      list.innerHTML = "";
      items = [];
      active = -1;
    };

    const highlight = () => {
      [...list.children].forEach((li, i) => li.classList.toggle("active", i === active));
    };

    const render = (suggestions) => {
      items = suggestions || [];
      active = -1;
      if (!items.length) return close();
      list.innerHTML = items
        .map((s, i) => `<li class="ac-item" data-i="${i}" role="option">${esc(s.description)}</li>`)
        .join("");
      list.hidden = false;
    };

    // Inserisce il comune scelto preservando la via gia' digitata.
    // Per i risultati Google (indirizzo completo) sostituisce tutto.
    const merge = (current, s) => {
      if (s.source === "google") return s.description;
      const name = s.municipality || s.description.replace(/\s*\([^)]*\)\s*$/, "");
      const comma = current.lastIndexOf(",");
      if (comma >= 0) return current.slice(0, comma + 1) + " " + name;
      return name;
    };

    const pick = (i) => {
      const s = items[i];
      if (!s) return;
      input.value = merge(input.value, s);
      close();
      if (onSelect) onSelect(s);
    };

    const query = async () => {
      const q = input.value.trim();
      if (q.length < 3) return close();
      if (q === lastQuery) return;
      lastQuery = q;
      try {
        const res = await fetch(`/api/geocode/suggest?q=${encodeURIComponent(q)}&limit=6`);
        if (!res.ok) return close();
        const data = await res.json();
        if (input.value.trim() !== q) return; // risposta obsoleta
        render(data.suggestions);
      } catch (e) {
        close();
      }
    };

    input.setAttribute("autocomplete", "off");
    input.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(query, 220);
    });
    input.addEventListener("keydown", (e) => {
      if (list.hidden) return;
      if (e.key === "ArrowDown") { e.preventDefault(); active = Math.min(items.length - 1, active + 1); highlight(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); active = Math.max(0, active - 1); highlight(); }
      else if (e.key === "Enter" && active >= 0) { e.preventDefault(); pick(active); }
      else if (e.key === "Escape") { close(); }
    });
    list.addEventListener("mousedown", (e) => {
      const li = e.target.closest(".ac-item");
      if (li) { e.preventDefault(); pick(Number(li.dataset.i)); }
    });
    input.addEventListener("blur", () => setTimeout(close, 150));
  }

  window.attachAutocomplete = attachAutocomplete;
})();
