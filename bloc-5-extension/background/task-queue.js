const QUEUE_KEY = "taskQueue";
const LAST_PUBLISH_KEY = "lastPublishedAt";
export const MIN_DELAY_BETWEEN_POSTS_MS = 4 * 60 * 60 * 1000; // 4h per route

async function readQueue() {
  return new Promise((r) =>
    chrome.storage.local.get(QUEUE_KEY, (d) => r(d[QUEUE_KEY] || []))
  );
}

async function writeQueue(q) {
  await chrome.storage.local.set({ [QUEUE_KEY]: q });
}

async function readLastPublished() {
  return new Promise((r) =>
    chrome.storage.local.get(LAST_PUBLISH_KEY, (d) => r(d[LAST_PUBLISH_KEY] || {}))
  );
}

function routeOf(task) {
  return task.publish_via || task.platform;
}

export async function enqueue(tasks) {
  const q = await readQueue();
  const ids = new Set(q.map((t) => t.task_id));
  for (const t of tasks) {
    if (!ids.has(t.task_id)) q.push({ ...t, status: "pending" });
  }
  await writeQueue(q);
}

export async function dequeue({ ignoreDelay = false } = {}) {
  const q = await readQueue();
  const last = await readLastPublished();
  const now = Date.now();
  // Anti-spam : au plus une publication toutes les 4h par route (le poll
  // suivant, 5 min plus tard, retentera les tasks encore bloquees).
  // ignoreDelay=true pour une publication manuelle explicite (bouton popup).
  const idx = q.findIndex(
    (t) => t.status === "pending" &&
      (ignoreDelay || now - (last[routeOf(t)] || 0) >= MIN_DELAY_BETWEEN_POSTS_MS)
  );
  if (idx === -1) return null;
  const task = q[idx];
  q[idx] = { ...task, status: "running" };
  await writeQueue(q);
  return task;
}

export async function markDone(taskId, result) {
  const q = await readQueue();
  const done = q.find((t) => t.task_id === taskId);
  const updated = q.map((t) =>
    t.task_id === taskId ? { ...t, status: "done", result, doneAt: Date.now() } : t
  );
  await writeQueue(updated.filter((t) => t.status !== "done" || Date.now() - t.doneAt < 3600_000));
  if (done) {
    const last = await readLastPublished();
    last[routeOf(done)] = Date.now();
    await chrome.storage.local.set({ [LAST_PUBLISH_KEY]: last });
  }
}

export async function markFailed(taskId, err) {
  const q = await readQueue();
  const updated = q.map((t) =>
    t.task_id === taskId ? { ...t, status: "failed", error: err } : t
  );
  await writeQueue(updated);
}

export async function getStats() {
  const q = await readQueue();
  return {
    pending: q.filter((t) => t.status === "pending").length,
    running: q.filter((t) => t.status === "running").length,
    done: q.filter((t) => t.status === "done").length,
    failed: q.filter((t) => t.status === "failed").length,
    last: q.filter((t) => t.status === "done" || t.status === "failed").at(-1) || null,
  };
}

export async function clearDone() {
  const q = await readQueue();
  await writeQueue(q.filter((t) => t.status !== "done" && t.status !== "failed"));
}
