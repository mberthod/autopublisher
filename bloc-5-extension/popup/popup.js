function $(id) { return document.getElementById(id); }

async function loadStats() {
  const stats = await chrome.runtime.sendMessage({ type: "GET_STATS" });
  if (!stats) return;
  $("stat-pending").textContent = stats.pending;
  $("stat-running").textContent = stats.running;
  $("stat-done").textContent = stats.done;
  $("stat-failed").textContent = stats.failed;

  if (stats.last) {
    const t = stats.last;
    const when = t.doneAt ? `il y a ${Math.round((Date.now() - t.doneAt) / 60000)} min` : "";
    const emoji = t.status === "done" ? "✓" : "✗";
    $("last-task").textContent = `${emoji} Dernière tâche (${t.platform}): ${t.status} ${when}`;
  }
}

async function loadSettings() {
  const { backendUrl } = await chrome.storage.local.get("backendUrl");
  if (backendUrl) $("backend-url").value = backendUrl;
}

$("btn-poll").addEventListener("click", async () => {
  $("btn-poll").disabled = true;
  $("btn-poll").textContent = "…";
  await chrome.runtime.sendMessage({ type: "FORCE_POLL" });
  await loadStats();
  $("btn-poll").disabled = false;
  $("btn-poll").textContent = "Vérifier maintenant";
});

$("btn-settings").addEventListener("click", () => {
  $("settings-panel").classList.toggle("hidden");
});

$("btn-save").addEventListener("click", async () => {
  const url = $("backend-url").value.trim();
  if (url) await chrome.storage.local.set({ backendUrl: url });
  $("settings-panel").classList.add("hidden");
});

loadStats();
loadSettings();
