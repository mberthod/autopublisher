import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { waitForElement } from "../content/shared/wait-for-element.js";

describe("waitForElement", () => {
  let container;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.removeChild(container);
  });

  it("resolves immediately if element already exists", async () => {
    const btn = document.createElement("button");
    btn.className = "test-btn";
    container.appendChild(btn);

    const el = await waitForElement(".test-btn", { root: container });
    expect(el).toBe(btn);
  });

  it("resolves when element appears after 1s (within 1.5s)", async () => {
    setTimeout(() => {
      const btn = document.createElement("button");
      btn.className = "late-btn";
      container.appendChild(btn);
    }, 1000);

    const start = Date.now();
    const el = await waitForElement(".late-btn", { root: container, timeoutMs: 5000 });
    const elapsed = Date.now() - start;

    expect(el).toBeTruthy();
    expect(elapsed).toBeGreaterThanOrEqual(900);
    expect(elapsed).toBeLessThan(1500);
  }, 6000);

  it("rejects after timeoutMs if element never appears", async () => {
    await expect(
      waitForElement(".never-appears", { root: container, timeoutMs: 500 })
    ).rejects.toThrow("not found after 500ms");
  }, 3000);
});
