(() => {
  // content/shared/wait-for-element.js
  function waitForElement(selector, { timeoutMs = 1e4, root = document } = {}) {
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

  // content/shared/human-typer.js
  function randomBetween(min, max) {
    return min + Math.random() * (max - min);
  }
  async function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }
  async function humanPause() {
    await sleep(randomBetween(1e3, 3e3));
  }
  async function typeText(element, text) {
    element.focus();
    for (const char of text) {
      if (element.isContentEditable) {
        const sel = window.getSelection();
        const range = sel?.getRangeAt(0);
        if (range) {
          const node = document.createTextNode(char);
          range.insertNode(node);
          range.setStartAfter(node);
          range.setEndAfter(node);
          sel.removeAllRanges();
          sel.addRange(range);
        }
        element.dispatchEvent(new InputEvent("input", { bubbles: true, data: char }));
      } else {
        element.value += char;
        element.dispatchEvent(new Event("input", { bubbles: true }));
      }
      await sleep(randomBetween(50, 150));
    }
  }
  async function humanClick(element) {
    await humanPause();
    const target = element.closest?.('button, a, [role="button"], [role="menuitem"], [role="tab"], label, [tabindex]') || element;
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    await sleep(randomBetween(300, 600));
    const opts = { bubbles: true, cancelable: true, view: window };
    target.dispatchEvent(new MouseEvent("mouseover", opts));
    await sleep(randomBetween(100, 300));
    target.dispatchEvent(new MouseEvent("mousedown", opts));
    await sleep(randomBetween(50, 150));
    target.dispatchEvent(new MouseEvent("mouseup", opts));
    target.dispatchEvent(new MouseEvent("click", opts));
    if (typeof target.click === "function") {
      try {
        target.click();
      } catch {
      }
    }
    await sleep(randomBetween(300, 600));
  }

  // content/shared/media-uploader.js
  async function uploadMediaFromUrl(fileInput, url, filename = "media.png", mediaData = null) {
    let blob;
    if (mediaData) {
      blob = new Blob([new Uint8Array(mediaData.bytes)], { type: mediaData.type || "image/png" });
      filename = mediaData.name || filename;
    } else {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`media download failed: HTTP ${response.status}`);
      blob = await response.blob();
    }
    const file = new File([blob], filename, { type: blob.type || "image/png" });
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    fileInput.dispatchEvent(new Event("change", { bubbles: true }));
    fileInput.dispatchEvent(new Event("input", { bubbles: true }));
  }

  // content/instagram-publisher.js
  var _initialized = false;
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg.type !== "PUBLISH_POST") return;
    if (_initialized) return;
    _initialized = true;
    publishInstagram(msg.task, msg.selectors).then((result) => sendResponse(result)).catch(
      (err) => sendResponse({
        status: "failed",
        error_code: "UNKNOWN",
        error_message: err.message
      })
    );
    return true;
  });
  async function clickButtonByText(texts, fallbackSel, timeoutMs = 1e4) {
    const deadline = Date.now() + timeoutMs;
    const needles = texts.map((t) => t.toLowerCase());
    while (Date.now() < deadline) {
      const candidates = document.querySelectorAll("div[role='button'], button, [role='button'] div");
      for (const el of candidates) {
        if (el.offsetHeight === 0) continue;
        const t = el.textContent.trim().toLowerCase();
        if (t && t.length < 20 && needles.some((n) => t === n || t.includes(n))) {
          await humanClick(el);
          return true;
        }
      }
      await new Promise((r) => setTimeout(r, 400));
    }
    const btn = await waitForElement(fallbackSel, { timeoutMs: 3e3 }).catch(() => null);
    if (btn) {
      await humanClick(btn);
      return true;
    }
    return false;
  }
  async function publishInstagram(task, sel) {
    const navCheck = document.querySelector("nav, a[href='/']");
    if (!navCheck) {
      return { status: "failed", error_code: "AUTH_REQUIRED", error_message: "Not logged into Instagram" };
    }
    try {
      if (!task.media_urls?.length) {
        return { status: "failed", error_code: "UNKNOWN", error_message: "Instagram requires at least one image" };
      }
      const newPostBtn = await waitForElement(sel.btn_new_post, { timeoutMs: 1e4 });
      await humanClick(newPostBtn);
      await humanPause();
      const fileInput = await waitForElement(sel.file_input, { timeoutMs: 1e4 });
      await uploadMediaFromUrl(fileInput, task.media_urls[0], `post_${task.post_id}.png`, task.media_data?.[0] ?? null);
      await humanPause();
      for (let i = 0; i < 2; i++) {
        const ok = await clickButtonByText(["suivant", "next"], sel.next_button, 12e3);
        if (!ok) return { status: "failed", error_code: "SELECTOR_NOT_FOUND", error_message: `Bouton 'Suivant' introuvable (etape ${i + 1})` };
        await humanPause();
      }
      if (task.text) {
        const caption = await waitForElement(sel.caption_editor, { timeoutMs: 1e4 });
        await humanClick(caption);
        await typeText(caption, task.text);
      }
      await humanPause();
      const shared = await clickButtonByText(["partager", "share"], sel.share_button, 12e3);
      if (!shared) return { status: "failed", error_code: "SELECTOR_NOT_FOUND", error_message: "Bouton 'Partager' introuvable" };
      const confirmed = await waitForElement(sel.success_indicator, { timeoutMs: 3e4 }).catch(() => null);
      if (!confirmed) {
        return {
          status: "failed",
          error_code: "PUBLISH_UNCONFIRMED",
          error_message: "No success indicator within 30s after clicking share"
        };
      }
      return { status: "success", post_url: null };
    } catch (err) {
      const code = err.message.includes("not found") ? "SELECTOR_NOT_FOUND" : "UNKNOWN";
      return { status: "failed", error_code: code, error_message: err.message };
    }
  }
})();
