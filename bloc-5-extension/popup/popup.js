function $(id) { return document.getElementById(id); }

// ---------- Connexion ----------

const LOGIN_URLS = {
  linkedin:  "https://www.linkedin.com/login",
  instagram: "https://www.instagram.com/accounts/login/",
  meta_suite: "https://business.facebook.com/latest/home",
};

// Demande au service-worker qui a acces aux tabs + cookies
async function loadConnections() {
  const fallback = { linkedin: false, instagram: false, meta_suite: false };
  let status = fallback;
  try {
    const result = await chrome.runtime.sendMessage({ type: "GET_CONNECTION_STATUS" });
    // sendMessage peut retourner null si le SW ne repond pas
    if (result && typeof result === "object") status = result;
  } catch {}

  for (const [platform, connected] of Object.entries(status)) {
    renderConnection(platform, connected);
  }
}

function renderConnection(platform, connected) {
  const statusEl = $(`status-${platform}`);
  const btnEl    = $(`btn-${platform}`);
  const badgeEl  = $(`badge-${platform}`);
  if (!statusEl || !btnEl || !badgeEl) return;

  if (connected) {
    statusEl.textContent = "Session active";
    statusEl.className   = "platform-status connected";
    btnEl.classList.add("hidden");
    badgeEl.classList.remove("hidden");
  } else {
    statusEl.textContent = "Non connecte";
    statusEl.className   = "platform-status disconnected";
    btnEl.classList.remove("hidden");
    badgeEl.classList.add("hidden");
  }
}

// Boutons "Se connecter"
for (const [platform, url] of Object.entries(LOGIN_URLS)) {
  $(`btn-${platform}`).addEventListener("click", () => {
    chrome.tabs.create({ url });
    window.close();
  });
}

// ---------- Synchronisation de session (cookies → serveur) ----------

$("btn-sync-session").addEventListener("click", async () => {
  const btn = $("btn-sync-session");
  const out = $("sync-result");
  btn.disabled = true;
  btn.textContent = "Synchronisation…";
  try {
    const resp = await chrome.runtime.sendMessage({ type: "SYNC_SESSIONS" });
    const results = resp?.results || [];
    const lines = results.map((r) =>
      r.ok ? `✅ ${r.platform} (${r.count} cookies)` : `⚠️ ${r.platform} : ${r.error}`
    );
    out.innerHTML = lines.join("<br>");
    out.classList.remove("hidden");
  } catch (e) {
    out.textContent = "Erreur : " + e.message;
    out.classList.remove("hidden");
  } finally {
    btn.disabled = false;
    btn.textContent = "🔄 Synchroniser mes sessions";
  }
});

// ---------- Onglet actif ----------

async function detectCurrentTab() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.url) return;
    const url = new URL(tab.url);
    const hostname = url.hostname;
    let label = null;

    if (hostname.includes("linkedin.com")) {
      const parts = tab.title?.split(" | ") || [];
      const name = (parts[0] || "LinkedIn").trim();
      label = "LinkedIn · " + name.substring(0, 35);
    } else if (hostname.includes("instagram.com")) {
      const name = (tab.title || "Instagram").replace("• Instagram", "").trim();
      label = "Instagram · " + name.substring(0, 35);
    }

    if (label) {
      $("current-tab").textContent = "📍 " + label;
      $("current-tab").classList.remove("hidden");
    }
  } catch {}
}

// ---------- Stats file de publication ----------

async function loadStats() {
  try {
    const stats = await chrome.runtime.sendMessage({ type: "GET_STATS" });
    if (!stats) return;
    $("stat-pending").textContent = stats.pending ?? "—";
    $("stat-running").textContent = stats.running ?? "—";
    $("stat-done").textContent    = stats.done    ?? "—";
    $("stat-failed").textContent  = stats.failed  ?? "—";

    if (stats.last) {
      const t    = stats.last;
      const when = t.doneAt ? "il y a " + Math.round((Date.now() - t.doneAt) / 60000) + " min" : "";
      const icon = t.status === "done" ? "✓" : "✗";
      $("last-task").textContent = (icon + " " + t.platform + " — " + t.status + " " + when).trim();
    }
  } catch {
    $("last-task").textContent = "Service worker non disponible.";
  }
}

// ---------- Parametres ----------

async function loadSettings() {
  const { backendUrl } = await chrome.storage.local.get("backendUrl");
  if (backendUrl) $("backend-url").value = backendUrl;
}

$("btn-poll").addEventListener("click", async () => {
  $("btn-poll").disabled    = true;
  $("btn-poll").textContent = "...";
  try {
    await chrome.runtime.sendMessage({ type: "FORCE_POLL" });
    await loadStats();
  } finally {
    $("btn-poll").disabled    = false;
    $("btn-poll").textContent = "▶ Publier maintenant";
  }
});

$("btn-settings").addEventListener("click", () => {
  $("settings-panel").classList.toggle("hidden");
});

$("btn-save").addEventListener("click", async () => {
  const url = $("backend-url").value.trim();
  if (url) await chrome.storage.local.set({ backendUrl: url });
  $("settings-panel").classList.add("hidden");
});

// ---------- Init ----------
loadConnections();
detectCurrentTab();
loadStats();
loadSettings();
