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
    element.scrollIntoView({ behavior: "smooth", block: "center" });
    await sleep(randomBetween(300, 600));
    element.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
    await sleep(randomBetween(100, 300));
    element.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    await sleep(randomBetween(50, 150));
    element.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
    element.click();
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
  async function publishInstagram(task, sel) {
    const navCheck = document.querySelector("nav, a[href='/']");
    if (!navCheck) {
      return { status: "failed", error_code: "AUTH_REQUIRED", error_message: "Not logged into Instagram" };
    }
    try {
      const newPostBtn = await waitForElement(sel.btn_new_post, { timeoutMs: 1e4 });
      await humanClick(newPostBtn);
      const fileInput = await waitForElement(sel.file_input, { timeoutMs: 1e4 });
      if (!task.media_urls?.length) {
        return { status: "failed", error_code: "UNKNOWN", error_message: "Instagram requires at least one image" };
      }
      await uploadMediaFromUrl(fileInput, task.media_urls[0], `post_${task.post_id}.png`, task.media_data?.[0] ?? null);
      await humanPause();
      for (let i = 0; i < 2; i++) {
        const nextBtn = await waitForElement(sel.next_button, { timeoutMs: 1e4 });
        await humanClick(nextBtn);
        await humanPause();
      }
      if (task.text) {
        const caption = await waitForElement(sel.caption_editor, { timeoutMs: 1e4 });
        await humanClick(caption);
        await typeText(caption, task.text);
      }
      await humanPause();
      const shareBtn = await waitForElement(sel.share_button, { timeoutMs: 1e4 });
      await humanClick(shareBtn);
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
