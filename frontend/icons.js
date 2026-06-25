"use strict";

/* ============================================================================
 * icons.js — Set di icone personalizzate (sprite SVG, tratto = currentColor).
 * Inietta lo sprite nel documento ed espone window.ICON(name, cls).
 * ========================================================================== */
(function () {
  const SPRITE = `
<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<symbol id="i-brick" viewBox="0 0 24 24"><rect x="3" y="4.5" width="18" height="4.3" rx="1"/><rect x="3" y="9.8" width="18" height="4.3" rx="1"/><rect x="3" y="15.1" width="18" height="4.3" rx="1"/><path d="M9 4.5v4.3M15 9.8v4.3M9 15.1v4.3M14 4.5v4.3"/></symbol>
<symbol id="i-shield" viewBox="0 0 24 24"><path d="M12 3l7 2.5v5.6c0 4.2-2.9 7.4-7 8.9-4.1-1.5-7-4.7-7-8.9V5.5L12 3z"/><path d="M8.6 12l2.2 2.2 4.6-4.6"/></symbol>
<symbol id="i-tag" viewBox="0 0 24 24"><path d="M3.5 12.5l8.5-8.5 7.5.8.8 7.5-8.5 8.5z"/><circle cx="14.7" cy="9.3" r="1.4"/></symbol>
<symbol id="i-bank" viewBox="0 0 24 24"><path d="M3 9.5l9-5 9 5"/><path d="M5 9.8v8M9 9.8v8M15 9.8v8M19 9.8v8"/><path d="M3.5 20.5h17"/></symbol>
<symbol id="i-building" viewBox="0 0 24 24"><rect x="5" y="3" width="14" height="18" rx="1.2"/><path d="M8.5 7h2M13.5 7h2M8.5 11h2M13.5 11h2M8.5 15h2M13.5 15h2"/><path d="M10 21v-3.2h4V21"/></symbol>
<symbol id="i-ruler" viewBox="0 0 24 24"><path d="M3 16.5L16.5 3l4.5 4.5L7.5 21z"/><path d="M7 12.5l1.8 1.8M10 9.5l1.8 1.8M13 6.5l1.8 1.8"/></symbol>
<symbol id="i-pin" viewBox="0 0 24 24"><path d="M12 21s6.5-6 6.5-10.5a6.5 6.5 0 10-13 0C5.5 15 12 21 12 21z"/><circle cx="12" cy="10.2" r="2.4"/></symbol>
<symbol id="i-key" viewBox="0 0 24 24"><circle cx="8" cy="8" r="4.2"/><path d="M11 11l8.5 8.5M16.5 16.5l2-2M18.5 18.5l2-2"/></symbol>
<symbol id="i-home" viewBox="0 0 24 24"><path d="M3 11l9-7 9 7"/><path d="M5.2 10v10h13.6V10"/><path d="M9.8 20v-5.4h4.4V20"/></symbol>
<symbol id="i-search" viewBox="0 0 24 24"><circle cx="11" cy="11" r="6.2"/><path d="M16 16l4.5 4.5"/></symbol>
<symbol id="i-coins" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.2"/><path d="M15 9.2a3.8 3.8 0 100 5.6M8 11h5.2M8 13h5.2"/></symbol>
<symbol id="i-doc" viewBox="0 0 24 24"><path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4"/><path d="M9.5 12h5M9.5 15h5M9.5 9h2"/></symbol>
</defs></svg>`;

  function inject() {
    if (document.getElementById("bv-sprite")) return;
    const holder = document.createElement("div");
    holder.id = "bv-sprite";
    holder.style.display = "none";
    holder.innerHTML = SPRITE;
    document.body.prepend(holder);
    // Intestazione visibile solo in stampa/PDF
    const ph = document.createElement("div");
    ph.className = "print-header";
    const today = new Date().toLocaleDateString("it-IT");
    ph.innerHTML = `<strong>brickvalue</strong><span>Valutazione immobiliare · ${today}</span>`;
    document.body.prepend(ph);
  }

  if (document.body) inject();
  else document.addEventListener("DOMContentLoaded", inject);

  window.ICON = (name, cls) => `<svg class="${cls || "ic"}" aria-hidden="true"><use href="#${name}"></use></svg>`;
})();
