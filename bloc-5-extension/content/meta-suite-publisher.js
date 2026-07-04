import { waitForElement } from "./shared/wait-for-element.js";
import { typeText, humanClick, humanPause } from "./shared/human-typer.js";
import { uploadMediaFromUrl } from "./shared/media-uploader.js";
import { identityMatches } from "./shared/identity.js";

let _initialized = false;

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type !== "PUBLISH_POST") return;
  if (_initialized) return;
  _initialized = true;

  publishMetaSuite(msg.task, msg.selectors)
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

function findByText(selector, text) {
  const els = document.querySelectorAll(selector);
  const needle = text.toLowerCase();
  return (
    Array.from(els).find((el) => el.textContent.trim().toLowerCase().includes(needle)) || null
  );
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
    } catch {}
  }
  return null;
}

async function ensureActiveAccount(sel, expectedName) {
  if (identityMatches(readActiveAccountName(sel), expectedName)) return null;

  const trigger = await waitForElement(sel.account_switcher_trigger, { timeoutMs: 8_000 }).catch(() => null);
  if (!trigger) return "account switcher not found";

  await humanClick(trigger);
  await new Promise((r) => setTimeout(r, 1200));

  const option = findByText(sel.account_option, expectedName);
  if (!option) return `account '${expectedName}' not found in switcher`;

  await humanClick(option);
  // Business Suite recharge la page/le contexte apres un switch
  await new Promise((r) => setTimeout(r, 4000));

  if (!identityMatches(readActiveAccountName(sel), expectedName)) {
    return `switch to '${expectedName}' did not take effect`;
  }
  return null;
}

async function selectPlacements(task, sel) {
  // Un Post = une plateforme : cocher la destination demandee, decocher l'autre.
  const placements = task.placements?.length ? task.placements : [task.platform];
  const toggles = {
    facebook: sel.placement_option_facebook,
    instagram: sel.placement_option_instagram,
  };
  for (const [platform, selector] of Object.entries(toggles)) {
    const el = document.querySelector(selector);
    if (!el) continue; // pas de choix de placement visible (compositeur mono-actif)
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
    await new Promise((r) => setTimeout(r, 4000));

    if (!document.querySelector("div[role='banner'], div[role='navigation']")) {
      return { status: "failed", error_code: "AUTH_REQUIRED", error_message: "Business Suite shell not loaded (not logged in?)" };
    }

    // ----- ETAPE 1 : verifier/selectionner l'actif (page FB / compte IG) -----
    if (task.publish_as_name) {
      const switchError = await ensureActiveAccount(sel, task.publish_as_name);
      if (switchError) {
        return {
          status: "failed",
          error_code: "WRONG_IDENTITY",
          error_message: `Actif '${task.publish_as_name}' non selectionne: ${switchError}`,
        };
      }
    }

    // ----- ETAPE 2 : ouvrir le compositeur (sauf si arrive via ?asset_id= composer direct) -----
    let editor = await waitForElement(sel.text_editor, { timeoutMs: 5_000 }).catch(() => null);
    if (!editor) {
      const createBtn = await waitForElement(sel.btn_create_post, { timeoutMs: 8_000 }).catch(() => null);
      if (createBtn) {
        await humanClick(createBtn);
      } else if (!clickByText(["créer une publication", "create post", "créer", "create"])) {
        throw new Error("Create post button not found");
      }
      await new Promise((r) => setTimeout(r, 2000));
      editor = await waitForElement(sel.text_editor, { timeoutMs: 12_000 });
    }

    // ----- ETAPE 3 : placements (Facebook / Instagram) -----
    await selectPlacements(task, sel);

    // ----- ETAPE 4 : texte -----
    await humanClick(editor);
    if (task.text) await typeText(editor, task.text);

    // ----- ETAPE 5 : media -----
    if (task.platform === "instagram" && !task.media_urls?.length) {
      return { status: "failed", error_code: "UNKNOWN", error_message: "Instagram requires at least one image" };
    }
    if (task.media_urls?.length > 0) {
      await humanPause();
      let fileInput = document.querySelector(sel.file_input);
      if (!fileInput) {
        const addMedia = await waitForElement(sel.btn_add_media, { timeoutMs: 5_000 }).catch(() => null);
        if (addMedia) {
          await humanClick(addMedia);
          await humanPause();
        }
        fileInput = await waitForElement(sel.file_input, { timeoutMs: 8_000 });
      }
      await uploadMediaFromUrl(
        fileInput,
        task.media_urls[0],
        `post_${task.post_id}.png`,
        task.media_data?.[0] ?? null
      );
      await humanPause();
    }

    // ----- ETAPE 6 : publier -----
    await humanPause();
    const publishBtn = await waitForElement(sel.btn_publish, { timeoutMs: 10_000 }).catch(() => null);
    if (publishBtn) {
      await humanClick(publishBtn);
    } else if (!clickByText(["publier", "publish"])) {
      throw new Error("Publish button not found");
    }

    // ----- ETAPE 7 : confirmation reelle -----
    const confirmed = await waitForElement(sel.success_indicator, { timeoutMs: 30_000 }).catch(() => null);
    if (!confirmed) {
      return {
        status: "failed",
        error_code: "PUBLISH_UNCONFIRMED",
        error_message: "No success indicator within 30s after clicking publish",
      };
    }

    return { status: "success", post_url: null };
  } catch (err) {
    const code = err.message.includes("not found") ? "SELECTOR_NOT_FOUND" : "UNKNOWN";
    return { status: "failed", error_code: code, error_message: err.message };
  }
}
