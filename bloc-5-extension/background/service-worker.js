import { fetchPendingTasks, postCallback } from "./api-client.js";
import { getSelectors } from "./remote-selectors.js";
import { enqueue, dequeue, markDone, markFailed, getStats } from "./task-queue.js";

const ALARM_POLL = "poll-tasks";
const ALARM_SELECTORS = "refresh-selectors";
const PLATFORM_URLS = {
  linkedin: "https://www.linkedin.com/feed/",
  instagram: "https://www.instagram.com/",
};

// Setup alarms on install/startup
chrome.runtime.onInstalled.addListener(setup);
chrome.runtime.onStartup.addListener(setup);

function setup() {
  chrome.alarms.create(ALARM_POLL, { periodInMinutes: 5 });
  chrome.alarms.create(ALARM_SELECTORS, { periodInMinutes: 360 });
}

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === ALARM_POLL) await pollAndProcess();
  if (alarm.name === ALARM_SELECTORS) await refreshSelectors();
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
});

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

  const platformUrl = PLATFORM_URLS[task.platform];
  if (!platformUrl) {
    await failTask(task, "UNKNOWN", `Unknown platform: ${task.platform}`);
    return;
  }

  let tab;
  try {
    tab = await chrome.tabs.create({ url: platformUrl, active: false });
    await waitForTabLoad(tab.id);

    const result = await chrome.tabs.sendMessage(tab.id, {
      type: "PUBLISH_POST",
      task,
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
