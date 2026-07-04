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

  // content/linkedin-publisher.js
  var _initialized = false;
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg.type !== "PUBLISH_POST") return;
    if (_initialized) return;
    _initialized = true;
    publishLinkedIn(msg.task, msg.selectors).then((result) => sendResponse(result)).catch(
      (err) => sendResponse({
        status: "failed",
        error_code: "UNKNOWN",
        error_message: err.message
      })
    );
    return true;
  });
  async function publishLinkedIn(task, sel) {
    const path = window.location.pathname;
    const isLoginPage = /^\/(login|checkpoint|signup|uas|session-expired)/.test(path);
    if (isLoginPage) {
      return { status: "failed", error_code: "AUTH_REQUIRED", error_message: "Not logged into LinkedIn" };
    }
    try {
      await waitForElement("div[data-view-name='feed-index-container'], main, div.feed-container-theme", { timeoutMs: 15e3 });
      await humanPause();
      let editor = document.querySelector("div[role='textbox'][contenteditable='true'], div.ql-editor[contenteditable='true']");
      if (!editor) {
        const composeSels = [
          sel.btn_open_compose,
          "button[aria-label*='post' i]",
          "button[aria-label*='Commencer' i]",
          "button[aria-label*='Start' i]",
          ".share-box-feed-entry__trigger",
          "div.share-box-feed-entry__top-bar button",
          "div[class*='share-box'] button",
          "div[class*='trigger'] button"
        ].filter(Boolean).join(", ");
        const composeBtn = await waitForElement(composeSels, { timeoutMs: 1e4 });
        await humanClick(composeBtn);
        editor = await waitForElement(
          "div[role='textbox'][contenteditable='true'], div.ql-editor[contenteditable='true']",
          { timeoutMs: 1e4 }
        );
      }
      await humanClick(editor);
      if (task.text) await typeText(editor, task.text);
      if (task.media_urls?.length > 0) {
        await humanPause();
        const fileInput = await waitForElement(sel.file_input, { timeoutMs: 5e3 });
        await uploadMediaFromUrl(fileInput, task.media_urls[0], `post_${task.post_id}.png`, task.media_data?.[0] ?? null);
        await humanPause();
      }
      await humanPause();
      const submitBtn = await waitForElement(sel.btn_submit, { timeoutMs: 1e4 });
      await humanClick(submitBtn);
      await waitForElement(sel.success_toast, { timeoutMs: 3e4 });
      return { status: "success", post_url: null };
    } catch (err) {
      const code = err.message.includes("not found") ? "SELECTOR_NOT_FOUND" : "UNKNOWN";
      return { status: "failed", error_code: code, error_message: err.message };
    }
  }
})();
