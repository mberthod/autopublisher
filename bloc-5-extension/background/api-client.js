// All backend calls. Backend URL is stored in chrome.storage.local.

const DEFAULT_BACKEND = "http://192.168.0.176:8000";

async function getBackendUrl() {
  return new Promise((resolve) => {
    chrome.storage.local.get("backendUrl", (r) =>
      resolve(r.backendUrl || DEFAULT_BACKEND)
    );
  });
}

export async function fetchPendingTasks() {
  const base = await getBackendUrl();
  const res = await fetch(`${base}/api/v1/tasks/pending`);
  if (!res.ok) throw new Error(`pending tasks: HTTP ${res.status}`);
  return res.json(); // { tasks: [...] }
}

export async function postCallback(taskId, payload) {
  const base = await getBackendUrl();
  const res = await fetch(`${base}/api/v1/tasks/${taskId}/callback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`callback: HTTP ${res.status}`);
  return res.json();
}

export async function postSession(platform, cookies, userAgent) {
  const base = await getBackendUrl();
  const res = await fetch(`${base}/api/v1/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ platform, cookies, user_agent: userAgent }),
  });
  if (!res.ok) throw new Error(`session: HTTP ${res.status}`);
  return res.json();
}

export async function postCapture(data) {
  const base = await getBackendUrl();
  await fetch(`${base}/api/v1/debug/capture`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function fetchSelectors(version) {
  const base = await getBackendUrl();
  const endpoint = version
    ? `${base}/api/v1/selectors/${version}`
    : `${base}/api/v1/selectors/latest`;
  const res = await fetch(endpoint);
  if (!res.ok) throw new Error(`selectors: HTTP ${res.status}`);
  return res.json();
}
