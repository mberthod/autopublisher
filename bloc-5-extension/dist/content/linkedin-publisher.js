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

  // content/shared/identity.js
  function normalizeName(s) {
    return (s || "").normalize("NFD").replace(new RegExp("\\p{Diacritic}", "gu"), "").toLowerCase().replace(/\s+/g, " ").trim();
  }
  function identityMatches(actual, expected) {
    const a = normalizeName(actual);
    const e = normalizeName(expected);
    if (!a || !e) return false;
    return a.includes(e) || e.includes(a);
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
  function clickByText(texts) {
    const candidates = document.querySelectorAll('button, [role="button"], a[class*="share"], div[class*="trigger"]');
    for (const el of candidates) {
      if (el.offsetHeight === 0) continue;
      const t = el.textContent.trim().toLowerCase();
      if (texts.some((kw) => t.includes(kw.toLowerCase()))) {
        el.click();
        return true;
      }
    }
    return false;
  }
  function domSnapshot() {
    const editables = [...document.querySelectorAll("[contenteditable]")].map((el) => {
      const cls = el.className ? el.className.toString().split(" ").slice(0, 3).join(".") : "";
      return `${el.tagName.toLowerCase()}${cls ? "." + cls : ""}[h=${el.offsetHeight},role=${el.getAttribute("role") || "-"},ph="${(el.getAttribute("data-placeholder") || "").substring(0, 20)}"]`;
    });
    const btns = [...document.querySelectorAll("button, [role='button']")].filter((b) => b.offsetHeight > 0).slice(0, 10).map((b) => `"${b.textContent.trim().substring(0, 30)}"[aria="${b.getAttribute("aria-label") || ""}"]`);
    return `contenteditable=[${editables.join(" | ") || "none"}] buttons=[${btns.join(", ")}]`;
  }
  async function waitForEditor(editorSelectors, timeoutMs = 15e3) {
    const selectors = editorSelectors.split(",").map((s) => s.trim()).filter(Boolean);
    return new Promise((resolve, reject) => {
      const deadline = Date.now() + timeoutMs;
      function check() {
        for (const sel of selectors) {
          try {
            const candidates = [...document.querySelectorAll(sel)];
            for (const el of candidates) {
              if (el.offsetHeight > 20 && !el.closest("nav") && !el.closest("header") && !el.closest("[class*='search']")) {
                return resolve(el);
              }
            }
          } catch {
          }
        }
        if (Date.now() > deadline) {
          return reject(new Error(`Editor not found on ${window.location.pathname}. ${domSnapshot()}`));
        }
        setTimeout(check, 400);
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
      await new Promise((r) => setTimeout(r, 3e3));
      const openTexts = ["cr\xE9er un post", "commencer un post", "start a post", "create a post", "commencer", "cr\xE9er", "share"];
      clickByText(openTexts);
      await new Promise((r) => setTimeout(r, 1500));
      let editor = null;
      try {
        editor = await waitForEditor(sel.text_editor, 8e3);
      } catch {
      }
      if (!editor) {
        const btn = await waitForElement(sel.btn_open_compose, { timeoutMs: 5e3 }).catch(() => null);
        if (btn) {
          await humanClick(btn);
          await new Promise((r) => setTimeout(r, 1500));
        } else {
          clickByText(openTexts);
          await new Promise((r) => setTimeout(r, 1500));
        }
        editor = await waitForEditor(sel.text_editor, 12e3);
      }
      if (task.publish_as_name) {
        const pickError = await selectPublishingIdentity(sel, task.publish_as_name);
        const identity = readPublishingIdentity(sel);
        if (!identityMatches(identity, task.publish_as_name)) {
          return {
            status: "failed",
            error_code: "WRONG_IDENTITY",
            error_message: `Compositeur en tant que '${identity || "inconnu"}' au lieu de '${task.publish_as_name}'` + (pickError ? ` (picker: ${pickError})` : "")
          };
        }
      }
      await humanClick(editor);
      if (task.text) await typeText(editor, task.text);
      if (task.media_urls?.length > 0) {
        await humanPause();
        const fileInput = await waitForElement(sel.file_input, { timeoutMs: 5e3 });
        await uploadMediaFromUrl(
          fileInput,
          task.media_urls[0],
          `post_${task.post_id}.png`,
          task.media_data?.[0] ?? null
        );
        await humanPause();
      }
      await humanPause();
      const submitBtn = await waitForElement(sel.btn_submit, { timeoutMs: 1e4 });
      await humanClick(submitBtn);
      await waitForElement(sel.success_toast, { timeoutMs: 3e4 });
      let postUrl = null;
      if (sel.success_toast_link) {
        const link = await waitForElement(sel.success_toast_link, { timeoutMs: 5e3 }).catch(() => null);
        if (link?.href) postUrl = link.href;
      }
      return { status: "success", post_url: postUrl };
    } catch (err) {
      const code = err.message.includes("not found") || err.message.includes("Editor not found") ? "SELECTOR_NOT_FOUND" : "UNKNOWN";
      return { status: "failed", error_code: code, error_message: err.message };
    }
  }
  function readPublishingIdentity(sel) {
    for (const s of sel.actor_name.split(",").map((x) => x.trim())) {
      try {
        const els = [...document.querySelectorAll(s)];
        for (const el of els) {
          if (el.offsetHeight === 0) continue;
          const t = el.textContent.trim();
          if (t) return t;
        }
      } catch {
      }
    }
    return null;
  }
  async function selectPublishingIdentity(sel, pageName) {
    try {
      if (identityMatches(readPublishingIdentity(sel), pageName)) return null;
      const pickerBtn = await waitForElement(sel.identity_picker_trigger, { timeoutMs: 5e3 }).catch(() => null);
      if (!pickerBtn) return "identity picker not found";
      await humanClick(pickerBtn);
      await new Promise((r) => setTimeout(r, 800));
      const option = findByText(sel.identity_option, pageName);
      if (!option) return `option '${pageName}' not found in picker`;
      await humanClick(option);
      await new Promise((r) => setTimeout(r, 500));
      return null;
    } catch (err) {
      return err.message;
    }
  }
})();
