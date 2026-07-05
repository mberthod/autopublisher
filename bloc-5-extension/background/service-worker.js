import { fetchPendingTasks, postCallback, postSession, postCapture } from "./api-client.js";
import { getSelectors } from "./remote-selectors.js";
import { enqueue, dequeue, markDone, markFailed, getStats } from "./task-queue.js";

const ALARM_POLL = "poll-tasks";
const ALARM_SELECTORS = "refresh-selectors";
const ALARM_ANALYTICS = "scrape-analytics";
const ALARM_SESSION = "sync-session";

// Domaines dont on capture les cookies pour rejouer la session cote serveur.
const SESSION_DOMAINS = {
  linkedin: "linkedin.com",
  instagram: "instagram.com",
  meta_suite: "facebook.com",
};

// Registre des surfaces de publication. Une task est routee par
// task.publish_via (calcule par le backend) avec fallback sur task.platform
// pour les tasks anterieures encore en queue.
const PLATFORM_REGISTRY = {
  linkedin: {
    // Pour publier en tant que PAGE, ouvrir l'espace ADMIN (contexte + x-li-page-instance requis).
    url: (task) => {
      if (task.page_url && task.page_url.includes("/company/")) {
        const id = task.page_url.split("/company/")[1].replace(/^\/+/, "").split("/")[0].split("?")[0];
        if (/^\d+$/.test(id)) return `https://www.linkedin.com/company/${id}/admin/page-posts/published/`;
      }
      return task.page_url || "https://www.linkedin.com/feed/?shareActive=true&shareContentType=post";
    },
    selectorsKey: (task) => task.platform,
    check: { urlPattern: "https://www.linkedin.com/*", loginRe: /\/(login|checkpoint|signup|uas)/, cookieUrl: "https://www.linkedin.com", cookieName: "li_at" },
  },
  instagram: {
    url: (task) => task.page_url || "https://www.instagram.com/",
    selectorsKey: (task) => task.platform,
    check: { urlPattern: "https://www.instagram.com/*", loginRe: /\/accounts\/(login|signup)/, cookieUrl: "https://www.instagram.com", cookieName: "sessionid" },
  },
  meta_suite: {
    url: (task) => task.asset_id
      ? `https://business.facebook.com/latest/composer?asset_id=${encodeURIComponent(task.asset_id)}`
      : "https://business.facebook.com/latest/home",
    selectorsKey: () => "meta_suite",
    check: { urlPattern: "https://business.facebook.com/*", loginRe: /\/(login|checkpoint)/, cookieUrl: "https://www.facebook.com", cookieName: "c_user" },
  },
};

// Setup alarms on install/startup
chrome.runtime.onInstalled.addListener(setup);
chrome.runtime.onStartup.addListener(setup);

function setup() {
  // Publication via l'API interne LinkedIn depuis CE navigateur (session native).
  chrome.alarms.create(ALARM_POLL, { periodInMinutes: 5 });
  chrome.alarms.create(ALARM_SELECTORS, { periodInMinutes: 360 });
  // Daily analytics scraping at 9:00 AM
  const now = new Date();
  const next9AM = new Date(now);
  next9AM.setHours(9, 0, 0, 0);
  if (next9AM <= now) next9AM.setDate(next9AM.getDate() + 1);
  chrome.alarms.create(ALARM_ANALYTICS, {
    when: next9AM.getTime(),
    periodInMinutes: 24 * 60,
  });
}

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === ALARM_POLL) await pollAndProcess();
  if (alarm.name === ALARM_SELECTORS) await refreshSelectors();
  if (alarm.name === ALARM_ANALYTICS) await scrapeAnalyticsForPublishedPosts();
});

// Capture les cookies d'une plateforme et les remonte au serveur, qui pourra
// rejouer la session via Playwright headless (publication PC eteint).
async function syncSession(platform) {
  const domain = SESSION_DOMAINS[platform];
  if (!domain) return { platform, ok: false, error: "unknown platform" };
  try {
    const cookies = await chrome.cookies.getAll({ domain });
    if (!cookies.length) return { platform, ok: false, error: "no cookies (not logged in?)" };
    await postSession(platform, cookies, navigator.userAgent);
    return { platform, ok: true, count: cookies.length };
  } catch (e) {
    return { platform, ok: false, error: e.message };
  }
}

async function syncAllSessions() {
  const results = [];
  for (const platform of Object.keys(SESSION_DOMAINS)) {
    results.push(await syncSession(platform));
  }
  return results;
}

// Allow popup to trigger an immediate poll
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "FORCE_POLL") {
    // Publier maintenant : ignore le delai anti-spam
    pollAndProcess({ manual: true }).then(() => sendResponse({ ok: true }));
    return true; // keep channel open for async
  }
  if (msg.type === "GET_STATS") {
    getStats().then((s) => sendResponse(s));
    return true;
  }
  if (msg.type === "LI_CAPTURE") {
    const { type, ...payload } = msg;
    postCapture(payload).catch(() => {});
    return false;
  }
  if (msg.type === "SYNC_SESSIONS") {
    syncAllSessions().then((results) => sendResponse({ results }));
    return true;
  }
  if (msg.type === "GET_CONNECTION_STATUS") {
    const keys = Object.keys(PLATFORM_REGISTRY);
    Promise.all(keys.map((k) => checkPlatformConnection(k))).then((results) => {
      const status = {};
      keys.forEach((k, i) => { status[k] = results[i]; });
      sendResponse(status);
    });
    return true;
  }
});

async function checkPlatformConnection(platform) {
  const cfg = PLATFORM_REGISTRY[platform]?.check;
  if (!cfg) return false;
  // Strategie 1 : verifier les onglets ouverts (pas de permission supplementaire)
  try {
    const tabs = await chrome.tabs.query({ url: cfg.urlPattern });
    if (tabs.some(t => t.url && !cfg.loginRe.test(new URL(t.url).pathname))) return true;
  } catch {}
  // Strategie 2 : verifier le cookie de session
  try {
    const cookie = await chrome.cookies.get({ url: cfg.cookieUrl, name: cfg.cookieName });
    if (cookie) return true;
  } catch {}
  return false;
}

async function refreshSelectors() {
  try {
    const { getSelectors } = await import("./remote-selectors.js");
    await getSelectors(null); // fetches latest, updates cache
  } catch (e) {
    console.warn("[SW] selector refresh failed:", e.message);
  }
}

async function pollAndProcess() {
  // Publication entièrement côté serveur : Instagram (instagrapi) + LinkedIn (Unipile).
  // L'extension ne publie plus ; elle ne sert qu'à capturer la session Instagram.
  return;
}

async function processNext({ manual = false } = {}) {
  const task = await dequeue({ ignoreDelay: manual });
  if (!task) return;

  let selectors;
  try {
    selectors = await getSelectors(task.selectors_version);
  } catch (e) {
    await failTask(task, "SELECTOR_NOT_FOUND", `Cannot load selectors: ${e.message}`);
    return;
  }

  const route = task.publish_via || task.platform;
  const platformCfg = PLATFORM_REGISTRY[route];
  if (!platformCfg) {
    await failTask(task, "UNKNOWN", `Unknown platform route: ${route}`);
    return;
  }
  const platformUrl = platformCfg.url(task);

  // Pre-fetch media bytes in the service worker context to bypass
  // Private Network Access restrictions in content scripts.
  const mediaData = [];
  for (const url of task.media_urls || []) {
    try {
      const r = await fetch(url);
      if (r.ok) {
        const buffer = await r.arrayBuffer();
        mediaData.push({
          name: url.split('/').pop().split('?')[0] || 'media.png',
          type: r.headers.get('content-type') || 'image/png',
          bytes: Array.from(new Uint8Array(buffer)),
        });
      }
    } catch (e) {
      console.warn('[SW] media prefetch failed', url, e.message);
    }
  }

  let tab;
  try {
    tab = await chrome.tabs.create({ url: platformUrl, active: false });
    await waitForTabLoad(tab.id);

    const result = await chrome.tabs.sendMessage(tab.id, {
      type: "PUBLISH_POST",
      task: { ...task, media_data: mediaData },
      selectors: selectors.platforms[platformCfg.selectorsKey(task)],
    });

    if (result?.status === "success") {
      await postCallback(task.task_id, {
        status: "success",
        post_url: result.post_url || null,
        published_at: new Date().toISOString(),
      });
      await markDone(task.task_id, result);
    } else {
      await failTask(task, result?.error_code || "UNKNOWN", result?.error_message || "Unknown error");
    }
  } catch (e) {
    await failTask(task, "UNKNOWN", e.message);
  } finally {
    if (tab?.id) {
      try { await chrome.tabs.remove(tab.id); } catch (_) {}
    }
  }
}

async function failTask(task, error_code, error_message) {
  try {
    await postCallback(task.task_id, { status: "failed", error_code, error_message });
  } catch (_) {}
  await markFailed(task.task_id, { error_code, error_message });
}

function waitForTabLoad(tabId, timeoutMs = 30_000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("tab load timeout")), timeoutMs);
    function onUpdated(id, info) {
      if (id === tabId && info.status === "complete") {
        clearTimeout(timer);
        chrome.tabs.onUpdated.removeListener(onUpdated);
        setTimeout(resolve, 1000); // extra 1s for JS to settle
      }
    }
    chrome.tabs.onUpdated.addListener(onUpdated);
  });
}
async function scrapeAnalyticsForPublishedPosts() {
  const base = await (async () => {
    return new Promise(r => chrome.storage.local.get("backendUrl", d => r(d.backendUrl || "http://192.168.0.176:8000")));
  })();

  let posts = [];
  try {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const dateStr = yesterday.toISOString().split("T")[0];
    const r = await fetch(`${base}/api/v1/posts?status=published&scheduled_for_date=${dateStr}`);
    posts = await r.json();
  } catch (e) {
    console.warn("[SW] analytics: could not fetch published posts", e.message);
    return;
  }

  for (const post of posts) {
    if (!post.published_url) continue;
    let tab;
    try {
      tab = await chrome.tabs.create({ url: post.published_url, active: false });
      await waitForTabLoad(tab.id);
      const metrics = await chrome.tabs.sendMessage(tab.id, {
        action: "scrapeAnalytics",
        platform: post.platform,
      });
      if (metrics) {
        await fetch(`${base}/api/v1/posts/${post.id}/metrics`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(metrics),
        });
      }
    } catch (e) {
      console.warn("[SW] analytics scrape failed for", post.id, e.message);
    } finally {
      if (tab?.id) { try { await chrome.tabs.remove(tab.id); } catch (_) {} }
    }
    // Pause between posts to avoid rate limiting
    await new Promise(r => setTimeout(r, 5000));
  }
}

