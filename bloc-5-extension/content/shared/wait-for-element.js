/**
 * Waits for a CSS selector to appear in the DOM using MutationObserver.
 * Resolves with the element or rejects after timeoutMs.
 */
export function waitForElement(selector, { timeoutMs = 10_000, root = document } = {}) {
  return new Promise((resolve, reject) => {
    const existing = root.querySelector(selector);
    if (existing) return resolve(existing);

    const timer = setTimeout(() => {
      observer.disconnect();
      reject(new Error(`waitForElement: "${selector}" not found after ${timeoutMs}ms`));
    }, timeoutMs);

    const observer = new MutationObserver(() => {
      const el = root.querySelector(selector);
      if (el) {
        clearTimeout(timer);
        observer.disconnect();
        resolve(el);
      }
    });

    observer.observe(root, { childList: true, subtree: true });
  });
}
