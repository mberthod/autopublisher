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

  // content/meta-suite-publisher.js
  var _initialized = false;
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg.type !== "PUBLISH_POST") return;
    if (_initialized) return;
    _initialized = true;
    publishMetaSuite(msg.task, msg.selectors).then((result) => sendResponse(result)).catch(
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
    const needle = text.toLowerCase();
    return Array.from(els).find((el) => el.textContent.trim().toLowerCase().includes(needle)) || null;
  }
  function clickByText(texts) {
    const candidates = document.querySelectorAll("div[role='button'], button, [role='menuitem']");
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
  function readActiveAccountName(sel) {
    for (const s of sel.active_account_name.split(",").map((x) => x.trim())) {
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
  async function ensureActiveAccount(sel, expectedName) {
    if (identityMatches(readActiveAccountName(sel), expectedName)) return null;
    const trigger = await waitForElement(sel.account_switcher_trigger, { timeoutMs: 8e3 }).catch(() => null);
    if (!trigger) return "account switcher not found";
    await humanClick(trigger);
    await new Promise((r) => setTimeout(r, 1200));
    const option = findByText(sel.account_option, expectedName);
    if (!option) return `account '${expectedName}' not found in switcher`;
    await humanClick(option);
    await new Promise((r) => setTimeout(r, 4e3));
    if (!identityMatches(readActiveAccountName(sel), expectedName)) {
      return `switch to '${expectedName}' did not take effect`;
    }
    return null;
  }
  async function selectPlacements(task, sel) {
    const placements = task.placements?.length ? task.placements : [task.platform];
    const toggles = {
      facebook: sel.placement_option_facebook,
      instagram: sel.placement_option_instagram
    };
    for (const [platform, selector] of Object.entries(toggles)) {
      const el = document.querySelector(selector);
      if (!el) continue;
      const checked = el.getAttribute("aria-checked") === "true" || el.checked === true;
      const wanted = placements.includes(platform);
      if (checked !== wanted) {
        await humanClick(el);
        await humanPause();
      }
    }
  }
  async function publishMetaSuite(task, sel) {
    if (/\/(login|checkpoint)/.test(window.location.pathname)) {
      return { status: "failed", error_code: "AUTH_REQUIRED", error_message: "Not logged into Meta Business Suite" };
    }
    try {
      await new Promise((r) => setTimeout(r, 4e3));
      if (!document.querySelector("div[role='banner'], div[role='navigation']")) {
        return { status: "failed", error_code: "AUTH_REQUIRED", error_message: "Business Suite shell not loaded (not logged in?)" };
      }
      if (task.publish_as_name) {
        const switchError = await ensureActiveAccount(sel, task.publish_as_name);
        if (switchError) {
          return {
            status: "failed",
            error_code: "WRONG_IDENTITY",
            error_message: `Actif '${task.publish_as_name}' non selectionne: ${switchError}`
          };
        }
      }
      let editor = await waitForElement(sel.text_editor, { timeoutMs: 5e3 }).catch(() => null);
      if (!editor) {
        const createBtn = await waitForElement(sel.btn_create_post, { timeoutMs: 8e3 }).catch(() => null);
        if (createBtn) {
          await humanClick(createBtn);
        } else if (!clickByText(["cr\xE9er une publication", "create post", "cr\xE9er", "create"])) {
          throw new Error("Create post button not found");
        }
        await new Promise((r) => setTimeout(r, 2e3));
        editor = await waitForElement(sel.text_editor, { timeoutMs: 12e3 });
      }
      await selectPlacements(task, sel);
      await humanClick(editor);
      if (task.text) await typeText(editor, task.text);
      if (task.platform === "instagram" && !task.media_urls?.length) {
        return { status: "failed", error_code: "UNKNOWN", error_message: "Instagram requires at least one image" };
      }
      if (task.media_urls?.length > 0) {
        await humanPause();
        let fileInput = document.querySelector(sel.file_input);
        if (!fileInput) {
          const addMedia = await waitForElement(sel.btn_add_media, { timeoutMs: 5e3 }).catch(() => null);
          if (addMedia) {
            await humanClick(addMedia);
            await humanPause();
          }
          fileInput = await waitForElement(sel.file_input, { timeoutMs: 8e3 });
        }
        await uploadMediaFromUrl(
          fileInput,
          task.media_urls[0],
          `post_${task.post_id}.png`,
          task.media_data?.[0] ?? null
        );
        await humanPause();
      }
      await humanPause();
      const publishBtn = await waitForElement(sel.btn_publish, { timeoutMs: 1e4 }).catch(() => null);
      if (publishBtn) {
        await humanClick(publishBtn);
      } else if (!clickByText(["publier", "publish"])) {
        throw new Error("Publish button not found");
      }
      const confirmed = await waitForElement(sel.success_indicator, { timeoutMs: 3e4 }).catch(() => null);
      if (!confirmed) {
        return {
          status: "failed",
          error_code: "PUBLISH_UNCONFIRMED",
          error_message: "No success indicator within 30s after clicking publish"
        };
      }
      return { status: "success", post_url: null };
    } catch (err) {
      const code = err.message.includes("not found") ? "SELECTOR_NOT_FOUND" : "UNKNOWN";
      return { status: "failed", error_code: code, error_message: err.message };
    }
  }
})();
