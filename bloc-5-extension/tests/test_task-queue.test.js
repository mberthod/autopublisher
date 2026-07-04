import { describe, it, expect, beforeEach } from "vitest";

// Mock minimal de chrome.storage.local (backing store en mémoire)
function installChromeMock() {
  const store = {};
  globalThis.chrome = {
    storage: {
      local: {
        get(key, cb) {
          const k = typeof key === "string" ? key : Object.keys(key)[0];
          cb({ [k]: store[k] });
        },
        set(obj) {
          Object.assign(store, obj);
          return Promise.resolve();
        },
      },
    },
  };
  return store;
}

describe("dequeue anti-spam (MIN_DELAY_BETWEEN_POSTS_MS)", () => {
  let store, mod;

  beforeEach(async () => {
    store = installChromeMock();
    // import après le mock pour que le module lise le bon chrome
    mod = await import("../background/task-queue.js");
  });

  it("bloque une task dont la route a publié il y a moins de 4h", async () => {
    const now = Date.now();
    store.taskQueue = [{ task_id: "t1", platform: "linkedin", status: "pending" }];
    store.lastPublishedAt = { linkedin: now - 60 * 60 * 1000 }; // 1h → bloqué
    const task = await mod.dequeue();
    expect(task).toBeNull();
  });

  it("laisse passer une task dont la route a publié il y a plus de 4h", async () => {
    const now = Date.now();
    store.taskQueue = [{ task_id: "t1", platform: "linkedin", status: "pending" }];
    store.lastPublishedAt = { linkedin: now - (4 * 60 * 60 * 1000 + 60_000) };
    const task = await mod.dequeue();
    expect(task?.task_id).toBe("t1");
  });

  it("laisse passer une route jamais publiée", async () => {
    store.taskQueue = [{ task_id: "t1", platform: "instagram", status: "pending" }];
    store.lastPublishedAt = {};
    const task = await mod.dequeue();
    expect(task?.task_id).toBe("t1");
  });

  it("traite les routes indépendamment", async () => {
    const now = Date.now();
    store.taskQueue = [
      { task_id: "li", platform: "linkedin", status: "pending" },
      { task_id: "ig", platform: "instagram", status: "pending" },
    ];
    store.lastPublishedAt = { linkedin: now - 60 * 60 * 1000 }; // LI bloqué, IG libre
    const task = await mod.dequeue();
    expect(task?.task_id).toBe("ig");
  });

  it("route par publish_via en priorité sur platform", async () => {
    const now = Date.now();
    store.taskQueue = [{ task_id: "t1", platform: "instagram", publish_via: "meta_suite", status: "pending" }];
    store.lastPublishedAt = { meta_suite: now - 60 * 60 * 1000 }; // meta_suite bloqué
    expect(await mod.dequeue()).toBeNull();
  });

  it("ignoreDelay=true (publication manuelle) bypasse le delai de 4h", async () => {
    const now = Date.now();
    store.taskQueue = [{ task_id: "t1", platform: "linkedin", status: "pending" }];
    store.lastPublishedAt = { linkedin: now - 60 * 1000 }; // 1 min → normalement bloqué
    expect(await mod.dequeue()).toBeNull();
    const task = await mod.dequeue({ ignoreDelay: true });
    expect(task?.task_id).toBe("t1");
  });

  it("markDone enregistre le timestamp de la route", async () => {
    store.taskQueue = [{ task_id: "t1", platform: "linkedin", status: "running" }];
    await mod.markDone("t1", { status: "success" });
    expect(store.lastPublishedAt.linkedin).toBeGreaterThan(0);
  });
});
