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
  function findByText(selector, text) {
    const els = document.querySelectorAll(selector);
    return Array.from(els).find((el) => el.textContent.trim().includes(text)) || null;
  }
  async function waitForEditor(timeoutMs = 15e3) {
    const selectors = [
      "div[role='textbox'][contenteditable='true']",
      "div.ql-editor[contenteditable='true']",
      "div[contenteditable='true'][data-placeholder]",
      "div[contenteditable='true'].editor-content",
      "div[contenteditable='true']"
    ];
    return new Promise((resolve, reject) => {
      const deadline = Date.now() + timeoutMs;
      function check() {
        for (const sel of selectors) {
          try {
            const el = document.querySelector(sel);
            if (el && el.offsetHeight > 30) return resolve(el);
          } catch {
          }
        }
        if (Date.now() > deadline) {
          return reject(new Error("LinkedIn composer editor not found after " + timeoutMs + "ms"));
        }
        setTimeout(check, 300);
      }
      check();
    });
  }
  async function publishLinkedIn(task, sel) {
    const path = window.location.pathname;
    if (/^\/(login|checkpoint|signup|uas|session-expired)/.test(path)) {
      return { status: "failed", error_code: "AUTH_REQUIRED", error_message: "Not logged into LinkedIn" };
    }
    try {
      await waitForElement(
        "div[data-view-name='feed-index-container'], main, div.feed-container-theme, div[class*='feed']",
        { timeoutMs: 15e3 }
      ).catch(() => null);
      await humanPause();
      await new Promise((r) => setTimeout(r, 2500));
      let editor = null;
      try {
        editor = await waitForEditor(5e3);
      } catch {
      }
      if (!editor) {
        const composeSels = [
          "button[aria-label='Commencer un post']",
          "button[aria-label='Start a post']",
          "button[aria-label='Demarrer un post']",
          ".share-box-feed-entry__trigger",
          "div.share-box-feed-entry__top-bar button",
          "div[class*='share-box'] button",
          "div[class*='trigger'] button"
        ].join(", ");
        const btn = await waitForElement(composeSels, { timeoutMs: 8e3 }).catch(() => null);
        if (btn) {
          await humanClick(btn);
          await new Promise((r) => setTimeout(r, 1500));
        }
        editor = await waitForEditor(12e3);
      }
      if (task.publish_as_name) {
        await selectPublishingIdentity(task.publish_as_name);
      }
      await humanClick(editor);
      if (task.text) await typeText(editor, task.text);
      if (task.media_urls?.length > 0) {
        await humanPause();
        const fileInput = await waitForElement(
          "input[type='file'][accept*='image'], input[type='file']",
          { timeoutMs: 5e3 }
        );
        await uploadMediaFromUrl(
          fileInput,
          task.media_urls[0],
          `post_${task.post_id}.png`,
          task.media_data?.[0] ?? null
        );
        await humanPause();
      }
      await humanPause();
      const submitSel = [
        "button.share-actions__primary-action",
        "button[class*='share-actions__primary']",
        "button[aria-label='Publier']",
        "button[aria-label='Post']",
        "button[aria-label='Partager']"
      ].join(", ");
      const submitBtn = await waitForElement(submitSel, { timeoutMs: 1e4 });
      await humanClick(submitBtn);
      await waitForElement("div[role='alert'], div[class*='artdeco-toast']", { timeoutMs: 3e4 });
      return { status: "success", post_url: null };
    } catch (err) {
      const code = err.message.includes("not found") ? "SELECTOR_NOT_FOUND" : "UNKNOWN";
      return { status: "failed", error_code: code, error_message: err.message };
    }
  }
  async function selectPublishingIdentity(pageName) {
    try {
      const pickerSel = [
        "button[aria-label*='Choisissez']",
        "button[aria-label*='Choose']",
        "button[aria-label*='identite']",
        "button[aria-label*='identity']",
        "div[class*='actor'] button",
        "div[class*='identity'] button",
        ".share-creation-state__actor-trigger",
        "button[class*='actor']"
      ].join(", ");
      const pickerBtn = await waitForElement(pickerSel, { timeoutMs: 5e3 }).catch(() => null);
      if (!pickerBtn) return;
      await humanClick(pickerBtn);
      await new Promise((r) => setTimeout(r, 800));
      const optionSels = [
        "[role='option']",
        "[role='radio']",
        "li[class*='actor']",
        "div[class*='actor-option']",
        "div[class*='identity-option']"
      ].join(", ");
      const option = findByText(optionSels, pageName);
      if (option) {
        await humanClick(option);
        await new Promise((r) => setTimeout(r, 500));
      }
    } catch {
    }
  }
})();
