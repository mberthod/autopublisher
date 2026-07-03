import { describe, it, expect, vi, beforeEach } from "vitest";

// Import only the sleep/typeText from the module
// We stub setTimeout to control timing
import { sleep, typeText, humanPause } from "../content/shared/human-typer.js";

describe("human-typer: sleep", () => {
  it("resolves after the given delay", async () => {
    const start = Date.now();
    await sleep(50);
    expect(Date.now() - start).toBeGreaterThanOrEqual(40);
  });
});

describe("human-typer: typeText timing", () => {
  it("types 50 chars in 2.5s–7.5s (50–150ms per char)", async () => {
    // Create a real contenteditable div
    const div = document.createElement("div");
    div.contentEditable = "true";
    document.body.appendChild(div);

    const text = "a".repeat(50);
    const start = Date.now();
    await typeText(div, text);
    const elapsed = Date.now() - start;

    expect(elapsed).toBeGreaterThanOrEqual(2400); // 50 * 50ms - margin
    expect(elapsed).toBeLessThan(8000);           // 50 * 150ms + margin
    document.body.removeChild(div);
  }, 15_000);
});

describe("human-typer: typeText on input", () => {
  it("appends characters to input value", async () => {
    const input = document.createElement("input");
    document.body.appendChild(input);
    await typeText(input, "hello");
    expect(input.value).toBe("hello");
    document.body.removeChild(input);
  }, 5_000);
});
