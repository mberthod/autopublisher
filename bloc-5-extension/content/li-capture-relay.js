// Content script (monde isolé) : injecte l'intercepteur dans la page et relaie
// les requêtes capturées vers le service worker → backend.
(function () {
  try {
    const s = document.createElement("script");
    s.src = chrome.runtime.getURL("content/li-capture.js");
    s.onload = () => s.remove();
    (document.head || document.documentElement).appendChild(s);
  } catch (e) {}

  window.addEventListener("message", (e) => {
    if (e.source === window && e.data && e.data.__liCapture) {
      const { __liCapture, ...payload } = e.data;
      chrome.runtime.sendMessage({ type: "LI_CAPTURE", ...payload });
    }
  });
})();
