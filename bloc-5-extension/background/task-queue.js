const QUEUE_KEY = "taskQueue";
const MIN_DELAY_BETWEEN_POSTS_MS = 4 * 60 * 60 * 1000; // 4h per platform

async function readQueue() {
  return new Promise((r) =>
    chrome.storage.local.get(QUEUE_KEY, (d) => r(d[QUEUE_KEY] || []))
  );
}

async function writeQueue(q) {
  await chrome.storage.local.set({ [QUEUE_KEY]: q });
}

export async function enqueue(tasks) {
  const q = await readQueue();
  const ids = new Set(q.map((t) => t.task_id));
  for (const t of tasks) {
    if (!ids.has(t.task_id)) q.push({ ...t, status: "pending" });
  }
  await writeQueue(q);
}

export async function dequeue() {
  const q = await readQueue();
  const idx = q.findIndex((t) => t.status === "pending");
  if (idx === -1) return null;
  const task = q[idx];
  q[idx] = { ...task, status: "running" };
  await writeQueue(q);
  return task;
}

export async function markDone(taskId, result) {
  const q = await readQueue();
  const updated = q.map((t) =>
    t.task_id === taskId ? { ...t, status: "done", result, doneAt: Date.now() } : t
  );
  await writeQueue(updated.filter((t) => t.status !== "done" || Date.now() - t.doneAt < 3600_000));
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
