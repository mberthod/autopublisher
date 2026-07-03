import { waitForElement } from "./shared/wait-for-element.js";
import { typeText, humanClick, humanPause } from "./shared/human-typer.js";
import { uploadMediaFromUrl } from "./shared/media-uploader.js";

let _initialized = false;

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type !== "PUBLISH_POST") return;
  if (_initialized) return;
  _initialized = true;

  publishInstagram(msg.task, msg.selectors)
    .then((result) => sendResponse(result))
    .catch((err) =>
      sendResponse({
        status: "failed",
        error_code: "UNKNOWN",
        error_message: err.message,
      })
    );
  return true;
});

async function publishInstagram(task, sel) {
  // Check logged in
  const navCheck = document.querySelector("nav, a[href='/']");
  if (!navCheck) {
    return { status: "failed", error_code: "AUTH_REQUIRED", error_message: "Not logged into Instagram" };
  }

  try {
    // Click new post icon
    const newPostBtn = await waitForElement(sel.btn_new_post, { timeoutMs: 10_000 });
    await humanClick(newPostBtn);

    // File input
    const fileInput = await waitForElement(sel.file_input, { timeoutMs: 10_000 });
    if (!task.media_urls?.length) {
      return { status: "failed", error_code: "UNKNOWN", error_message: "Instagram requires at least one image" };
    }

    await uploadMediaFromUrl(fileInput, task.media_urls[0], `post_${task.post_id}.png`);
    await humanPause();

    // Next → Next → Caption
    for (let i = 0; i < 2; i++) {
      const nextBtn = await waitForElement(sel.next_button, { timeoutMs: 10_000 });
      await humanClick(nextBtn);
      await humanPause();
    }

    // Write caption
    if (task.text) {
      const caption = await waitForElement(sel.caption_editor, { timeoutMs: 10_000 });
      await humanClick(caption);
      await typeText(caption, task.text);
    }

    // Share
    await humanPause();
    const shareBtn = await waitForElement(sel.share_button, { timeoutMs: 10_000 });
    await humanClick(shareBtn);

    return { status: "success", post_url: null };
  } catch (err) {
    const code = err.message.includes("not found") ? "SELECTOR_NOT_FOUND" : "UNKNOWN";
    return { status: "failed", error_code: code, error_message: err.message };
  }
}
