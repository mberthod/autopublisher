import { fetchPendingTasks, postCallback } from "./api-client.js";
import { getSelectors } from "./remote-selectors.js";
import { enqueue, dequeue, markDone, markFailed, getStats } from "./task-queue.js";

const ALARM_POLL = "poll-tasks";
const ALARM_SELECTORS = "refresh-selectors";
const ALARM_ANALYTICS = "scrape-analytics";
const PLATFORM_URLS = {
  linkedin: "https://www.linkedin.com/feed/?shareActive=true&shareContentType=post",
  instagram: "https://www.instagram.com/",
};

// Setup alarms on install/startup
chrome.runtime.onInstalled.addListener(setup);
chrome.runtime.onStartup.addListener(setup);

function setup() {
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

// Allow popup to trigger an immediate poll
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "FORCE_POLL") {
    pollAndProcess().then(() => sendResponse({ ok: true }));
    return true; // keep channel open for async
  }
  if (msg.type === "GET_STATS") {
    getStats().then((s) => sendResponse(s));
    return true;
  }
  if (msg.type === "GET_CONNECTION_STATUS") {
    Promise.all([
      checkPlatformConnection("linkedin"),
      checkPlatformConnection("instagram"),
    ]).then(([linkedin, instagram]) => sendResponse({ linkedin, instagram }));
    return true;
  }
});

const PLATFORM_CHECK = {
  linkedin:  { urlPattern: "https://www.linkedin.com/*", loginRe: /\/(login|checkpoint|signup|uas)/, cookieUrl: "https://www.linkedin.com",  cookieName: "li_at" },
  instagram: { urlPattern: "https://www.instagram.com/*", loginRe: /\/accounts\/(login|signup)/,    cookieUrl: "https://www.instagram.com", cookieName: "sessionid" },
};

async function checkPlatformConnection(platform) {
  const cfg = PLATFORM_CHECK[platform];
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
  try {
    const { tasks } = await fetchPendingTasks();
    if (tasks.length > 0) await enqueue(tasks);
  } catch (e) {
    console.warn("[SW] poll failed:", e.message);
  }
  await processNext();
}

async function processNext() {
  const task = await dequeue();
  if (!task) return;

  let selectors;
  try {
    selectors = await getSelectors(task.selectors_version);
  } catch (e) {
    await failTask(task, "SELECTOR_NOT_FOUND", `Cannot load selectors: ${e.message}`);
    return;
  }

  const platformUrl = task.page_url || PLATFORM_URLS[task.platform];
  if (!platformUrl) {
    await failTask(task, "UNKNOWN", `Unknown platform: ${task.platform}`);
    return;
  }

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
      selectors: selectors.platforms[task.platform],
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

