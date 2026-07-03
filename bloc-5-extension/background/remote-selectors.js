import { fetchSelectors } from "./api-client.js";

const CACHE_KEY = "selectorsCache";
const TTL_MS = 6 * 60 * 60 * 1000; // 6h

export async function getSelectors(version) {
  const cached = await new Promise((r) =>
    chrome.storage.local.get(CACHE_KEY, (d) => r(d[CACHE_KEY] || null))
  );

  const cacheHit =
    cached &&
    (!version || cached.version === version) &&
    Date.now() - cached.fetchedAt < TTL_MS;

  if (cacheHit) return cached.data;

  try {
    const data = await fetchSelectors(version);
    await chrome.storage.local.set({
      [CACHE_KEY]: { version: data.version, data, fetchedAt: Date.now() },
    });
    return data;
  } catch (err) {
    // degraded mode: use stale cache if available
    if (cached) return cached.data;
    throw err;
  }
}

export async function invalidateSelectorsCache() {
  await chrome.storage.local.remove(CACHE_KEY);
}
