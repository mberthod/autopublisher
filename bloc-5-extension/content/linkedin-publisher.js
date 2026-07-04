import { waitForElement } from "./shared/wait-for-element.js";
import { typeText, humanClick, humanPause } from "./shared/human-typer.js";
import { uploadMediaFromUrl } from "./shared/media-uploader.js";

let _initialized = false;

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type !== "PUBLISH_POST") return;
  if (_initialized) return; // prevent double-run if CS loaded twice
  _initialized = true;

  publishLinkedIn(msg.task, msg.selectors)
    .then((result) => sendResponse(result))
    .catch((err) =>
      sendResponse({
        status: "failed",
        error_code: "UNKNOWN",
        error_message: err.message,
      })
    );
  return true; // async
});

async function publishLinkedIn(task, sel) {
  // Check we're logged in — works on personal feed AND company admin pages
  const path = window.location.pathname;
  const isLoginPage = /^\/(login|checkpoint|signup|uas|session-expired)/.test(path);
  if (isLoginPage) {
    return { status: "failed", error_code: "AUTH_REQUIRED", error_message: "Not logged into LinkedIn" };
  }

  try {
    // Attendre que la page soit chargee (le feed doit etre visible)
    await waitForElement("div[data-view-name='feed-index-container'], main, div.feed-container-theme", { timeoutMs: 15_000 });
    await humanPause();

    // Le parametre ?shareActive=true peut avoir deja ouvert le compositeur.
    // Sinon on cherche et clique le bouton compose.
    let editor = document.querySelector("div[role='textbox'][contenteditable='true'], div.ql-editor[contenteditable='true']");

    if (!editor) {
      // Chercher le bouton d'ouverture du compositeur avec fallbacks larges
      const composeSels = [
        sel.btn_open_compose,
        "button[aria-label*='post' i]",
        "button[aria-label*='Commencer' i]",
        "button[aria-label*='Start' i]",
        ".share-box-feed-entry__trigger",
        "div.share-box-feed-entry__top-bar button",
        "div[class*='share-box'] button",
        "div[class*='trigger'] button",
      ].filter(Boolean).join(", ");

      const composeBtn = await waitForElement(composeSels, { timeoutMs: 10_000 });
      await humanClick(composeBtn);

      editor = await waitForElement(
        "div[role='textbox'][contenteditable='true'], div.ql-editor[contenteditable='true']",
        { timeoutMs: 10_000 }
      );
    }

    await humanClick(editor);
    if (task.text) await typeText(editor, task.text);

    // Upload media if any
    if (task.media_urls?.length > 0) {
      await humanPause();
      const fileInput = await waitForElement(sel.file_input, { timeoutMs: 5_000 });
      await uploadMediaFromUrl(fileInput, task.media_urls[0], `post_${task.post_id}.png`, task.media_data?.[0] ?? null);
      await humanPause();
    }

    // Submit
    await humanPause();
    const submitBtn = await waitForElement(sel.btn_submit, { timeoutMs: 10_000 });
    await humanClick(submitBtn);

    // Wait for success toast
    await waitForElement(sel.success_toast, { timeoutMs: 30_000 });

    return { status: "success", post_url: null };
  } catch (err) {
    const code = err.message.includes("not found") ? "SELECTOR_NOT_FOUND" : "UNKNOWN";
    return { status: "failed", error_code: code, error_message: err.message };
  }
}

