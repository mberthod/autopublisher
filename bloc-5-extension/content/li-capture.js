// Contexte PAGE (main world) : observe les requêtes que LinkedIn émet vers son
// API interne et copie les en-têtes techniques (x-li-track avec la bonne version,
// x-li-page-instance, x-li-lang) dans des data-attributes du <html>. Le publisher
// (monde isolé) les relit — plus besoin de capture manuelle.
(function () {
  if (window.__liHdrInstalled) return;
  window.__liHdrInstalled = true;

  function ser(h) {
    try {
      if (!h) return null;
      if (h instanceof Headers) { const o = {}; h.forEach((v, k) => (o[k.toLowerCase()] = v)); return o; }
      if (Array.isArray(h)) { const o = {}; h.forEach(([k, v]) => (o[String(k).toLowerCase()] = v)); return o; }
      const o = {}; for (const k in h) o[k.toLowerCase()] = h[k]; return o;
    } catch (e) { return null; }
  }

  function stash(headers) {
    const h = ser(headers);
    if (!h) return;
    const el = document.documentElement;
    if (h["x-li-track"]) el.setAttribute("data-li-track", h["x-li-track"]);
    if (h["x-li-page-instance"]) el.setAttribute("data-li-page-instance", h["x-li-page-instance"]);
    if (h["x-li-lang"]) el.setAttribute("data-li-lang", h["x-li-lang"]);
  }

  const origFetch = window.fetch;
  window.fetch = function (input, init) {
    try {
      const isReq = typeof Request !== "undefined" && input instanceof Request;
      const url = isReq ? input.url : (typeof input === "string" ? input : (input && input.url) || "");
      if (/\/voyager\/api\//.test(url)) {
        stash((init && init.headers) || (isReq ? input.headers : null));
      }
    } catch (e) {}
    return origFetch.apply(this, arguments);
  };
})();
