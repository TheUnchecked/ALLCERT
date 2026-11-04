// Logica di analisi dei dati: raggruppamento degli aggiornamenti, gravità e prodotto.
// Usabile sia nel browser (window.Analisi) sia in Node per i test (require).
(function (root) {
  "use strict";

  const TAG_INIZIALI = /^(?:\s*\[[^\]]*\]\s*)+/;

  // Livelli di gravità: solo i bollettini che la indicano in modo strutturato (CERT-Bund: [kritisch], [hoch]...).
  const LIVELLI = { kritisch: 4, hoch: 3, mittel: 2, niedrig: 1 };
  const NOMI_LIVELLO = { 4: "Critica", 3: "Alta", 2: "Media", 1: "Bassa" };

  function senzaTag(titolo) {
    return String(titolo || "").replace(TAG_INIZIALI, "").replace(/\s+/g, " ").trim();
  }

  function normTitolo(titolo) {
    return senzaTag(titolo).toLowerCase();
  }

  function gravita(titolo) {
    const m = String(titolo || "").match(TAG_INIZIALI);
    if (!m) return 0;
    let max = 0;
    for (const t of m[0].match(/\[([^\]]*)\]/g) || []) {
      const livello = LIVELLI[t.slice(1, -1).trim().toLowerCase()];
      if (livello > max) max = livello;
    }
    return max;
  }

  function pulisciProdotto(s) {
    let p = String(s || "")
      .replace(/\s*\([^)]*\)/g, "")          // parentesi: (kernel), (03 novembre 2026)...
      .replace(/^(?:prodotti|products|produits)\s+/i, "")
      .replace(/\s+/g, " ")
      .replace(/[.:;,\s]+$/, "")
      .trim();
    return p.length >= 2 && p.length <= 40 ? p : null;
  }

  // Ricava il prodotto interessato dal titolo, con una regola per ciascuna fonte.
  // E' un'indicazione ricavata dal testo: dove la regola non si applica restituisce null.
  function prodotto(voce) {
    const t = senzaTag(voce.title);
    const fonte = voce.source || "";
    let m;
    if (fonte.startsWith("cert-bund")) {
      const i = t.indexOf(":");
      return i > 0 ? pulisciProdotto(t.slice(0, i)) : null;
    }
    if (fonte === "csirt-it") {
      m = t.match(/vulnerabilit[àa]\s+(?:critiche\s+|zero-day\s+)?(?:in|nei|negli|nel|su)\s+(?:prodotti\s+)?(.+)$/i);
      return m ? pulisciProdotto(m[1]) : null;
    }
    if (fonte === "cert-fr") {
      m = t.match(/vuln[ée]rabilit[ée]s?\s+(?:critiques?\s+)?dans\s+(.+)$/i);
      return m ? pulisciProdotto(m[1]) : null;
    }
    if (fonte === "cert-eu") {
      m = t.match(/vulnerabilit(?:y|ies)\s+in\s+(.+)$/i);
      return m ? pulisciProdotto(m[1]) : null;
    }
    return null;
  }

  // Unisce le voci con stessa fonte e stesso titolo (senza etichette [UPDATE], [mittel]...).
  // Restituisce i gruppi, dal più recente: main = voce più recente, membri = tutte le versioni.
  function raggruppa(voci, tempo, unisci = true) {
    const gruppi = new Map();
    for (const v of voci) {
      // Con unisci=false ogni voce resta un gruppo a sé.
      // La gravità fa parte della chiave: due voci con lo stesso titolo ma gravità diversa sono avvisi diversi.
      const chiave = unisci ? v.source + "|" + gravita(v.title) + "|" + normTitolo(v.title) : v.id;
      let g = gruppi.get(chiave);
      if (!g) { g = { key: chiave, membri: [] }; gruppi.set(chiave, g); }
      g.membri.push(v);
    }
    const lista = [];
    for (const g of gruppi.values()) {
      g.membri.sort((a, b) => tempo(b) - tempo(a));
      g.main = g.membri[0];
      g.tempo = tempo(g.main);
      g.gravita = Math.max(...g.membri.map(m => gravita(m.title)));
      g.cves = [...new Set(g.membri.flatMap(m => m.cves || []))].sort();
      lista.push(g);
    }
    return lista.sort((a, b) => b.tempo - a.tempo);
  }

  const API = { senzaTag, normTitolo, gravita, prodotto, raggruppa, NOMI_LIVELLO };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  else root.Analisi = API;
})(typeof window !== "undefined" ? window : globalThis);
