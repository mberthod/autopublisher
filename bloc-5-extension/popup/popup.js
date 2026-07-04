function $(id) { return document.getElementById(id); }

// ---------- Connexion (vérification via cookies) ----------

const PLATFORMS = {
  linkedin:  { cookieUrl: "https://www.linkedin.com", cookieName: "li_at",    loginUrl: "https://www.linkedin.com/login" },
  instagram: { cookieUrl: "https://www.instagram.com", cookieName: "sessionid", loginUrl: "https://www.instagram.com/accounts/login/" },
};

async function isConnected(platform) {
  try {
    const cfg = PLATFORMS[platform];
    const cookie = await chrome.cookies.get({ url: cfg.cookieUrl, name: cfg.cookieName });
    return !!cookie;
  } catch {
    return false;
  }
}

function renderConnection(platform, connected) {
  const statusEl = $(`status-${platform}`);
  const btnEl    = $(`btn-${platform}`);
  const badgeEl  = $(`badge-${platform}`);

  if (connected) {
    statusEl.textContent = "Session active";
    statusEl.className   = "platform-status connected";
    btnEl.classList.add("hidden");
    badgeEl.classList.remove("hidden");
  } else {
    statusEl.textContent = "Non connecté";
    statusEl.className   = "platform-status disconnected";
    btnEl.classList.remove("hidden");
    badgeEl.classList.add("hidden");
  }
}

async function loadConnections() {
  for (const platform of Object.keys(PLATFORMS)) {
    const connected = await isConnected(platform);
    renderConnection(platform, connected);
  }
}

// Boutons "Se connecter"
for (const [platform, cfg] of Object.entries(PLATFORMS)) {
  $(`btn-${platform}`).addEventListener("click", () => {
    chrome.tabs.create({ url: cfg.loginUrl });
    window.close(); // ferme le popup
  });
}

// ---------- Stats de la file de publication ----------

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
      const when = t.doneAt ? `il y a ${Math.round((Date.now() - t.doneAt) / 60000)} min` : "";
      const icon = t.status === "done" ? "✓" : "✗";
      $("last-task").textContent = `${icon} ${t.platform} — ${t.status} ${when}`.trim();
    }
  } catch {
    $("last-task").textContent = "Service worker non disponible.";
  }
}

// ---------- Paramètres ----------

async function loadSettings() {
  const { backendUrl } = await chrome.storage.local.get("backendUrl");
  if (backendUrl) $("backend-url").value = backendUrl;
}

$("btn-poll").addEventListener("click", async () => {
  $("btn-poll").disabled    = true;
  $("btn-poll").textContent = "…";
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
loadStats();
loadSettings();
