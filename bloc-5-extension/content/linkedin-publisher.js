import { waitForElement } from "./shared/wait-for-element.js";
import { typeText, humanClick, humanPause } from "./shared/human-typer.js";
import { uploadMediaFromUrl } from "./shared/media-uploader.js";

let _initialized = false;

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type !== "PUBLISH_POST") return;
  if (_initialized) return;
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
  return true;
});

// Trouve un element contenant un texte specifique parmi plusieurs selecteurs
function findByText(selector, text) {
  const els = document.querySelectorAll(selector);
  return Array.from(els).find((el) => el.textContent.trim().includes(text)) || null;
}

// Attendre qu'un element contenteditable apparaisse (LinkedIn n'utilise pas toujours role=textbox)
async function waitForEditor(timeoutMs = 15_000) {
  const selectors = [
    "div[role='textbox'][contenteditable='true']",
    "div.ql-editor[contenteditable='true']",
    "div[contenteditable='true'][data-placeholder]",
    "div[contenteditable='true'].editor-content",
    "div[contenteditable='true']",
  ];

  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeoutMs;

    function check() {
      for (const sel of selectors) {
        try {
          const el = document.querySelector(sel);
          // Ignorer les elements tres petits ou dans les nav (faux positifs)
          if (el && el.offsetHeight > 30) return resolve(el);
        } catch {}
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
  // Check login
  const path = window.location.pathname;
  if (/^\/(login|checkpoint|signup|uas|session-expired)/.test(path)) {
    return { status: "failed", error_code: "AUTH_REQUIRED", error_message: "Not logged into LinkedIn" };
  }

  try {
    // Attendre que le feed soit charge
    await waitForElement(
      "div[data-view-name='feed-index-container'], main, div.feed-container-theme, div[class*='feed']",
      { timeoutMs: 15_000 }
    ).catch(() => null); // non-bloquant si non trouve
    await humanPause();

    // Laisser le temps au modal ?shareActive=true de s'ouvrir
    await new Promise((r) => setTimeout(r, 2500));

    // ----- ETAPE 1 : trouver ou ouvrir le compositeur -----
    let editor = null;
    try {
      editor = await waitForEditor(5_000);
    } catch {}

    if (!editor) {
      // Le modal ne s'est pas ouvert automatiquement -> cliquer le bouton compose
      const composeSels = [
        "button[aria-label='Commencer un post']",
        "button[aria-label='Start a post']",
        "button[aria-label='Demarrer un post']",
        ".share-box-feed-entry__trigger",
        "div.share-box-feed-entry__top-bar button",
        "div[class*='share-box'] button",
        "div[class*='trigger'] button",
      ].join(", ");

      const btn = await waitForElement(composeSels, { timeoutMs: 8_000 }).catch(() => null);
      if (btn) {
        await humanClick(btn);
        await new Promise((r) => setTimeout(r, 1500));
      }
      editor = await waitForEditor(12_000);
    }

    // ----- ETAPE 2 : selectionner le compte entreprise -----
    if (task.publish_as_name) {
      await selectPublishingIdentity(task.publish_as_name);
    }

    // ----- ETAPE 3 : taper le texte -----
    await humanClick(editor);
    if (task.text) await typeText(editor, task.text);

    // ----- ETAPE 4 : uploader un media si besoin -----
    if (task.media_urls?.length > 0) {
      await humanPause();
      const fileInput = await waitForElement(
        "input[type='file'][accept*='image'], input[type='file']",
        { timeoutMs: 5_000 }
      );
      await uploadMediaFromUrl(
        fileInput,
        task.media_urls[0],
        `post_${task.post_id}.png`,
        task.media_data?.[0] ?? null
      );
      await humanPause();
    }

    // ----- ETAPE 5 : publier -----
    await humanPause();
    const submitSel = [
      "button.share-actions__primary-action",
      "button[class*='share-actions__primary']",
      "button[aria-label='Publier']",
      "button[aria-label='Post']",
      "button[aria-label='Partager']",
    ].join(", ");
    const submitBtn = await waitForElement(submitSel, { timeoutMs: 10_000 });
    await humanClick(submitBtn);

    // ----- ETAPE 6 : attendre la confirmation -----
    await waitForElement("div[role='alert'], div[class*='artdeco-toast']", { timeoutMs: 30_000 });

    return { status: "success", post_url: null };
  } catch (err) {
    const code = err.message.includes("not found") ? "SELECTOR_NOT_FOUND" : "UNKNOWN";
    return { status: "failed", error_code: code, error_message: err.message };
  }
}

// Selectionner le compte entreprise dans le picker d'identite du compositeur
async function selectPublishingIdentity(pageName) {
  try {
    // Trouver le bouton identity picker (montre la photo de profil actuelle)
    const pickerSel = [
      "button[aria-label*='Choisissez']",
      "button[aria-label*='Choose']",
      "button[aria-label*='identite']",
      "button[aria-label*='identity']",
      "div[class*='actor'] button",
      "div[class*='identity'] button",
      ".share-creation-state__actor-trigger",
      "button[class*='actor']",
    ].join(", ");

    const pickerBtn = await waitForElement(pickerSel, { timeoutMs: 5_000 }).catch(() => null);

    if (!pickerBtn) return; // pas de picker = deja le bon compte ou non supporte

    await humanClick(pickerBtn);
    await new Promise((r) => setTimeout(r, 800));

    // Chercher l'option contenant le nom de la page entreprise
    const optionSels = [
      "[role='option']",
      "[role='radio']",
      "li[class*='actor']",
      "div[class*='actor-option']",
      "div[class*='identity-option']",
    ].join(", ");

    const option = findByText(optionSels, pageName);
    if (option) {
      await humanClick(option);
      await new Promise((r) => setTimeout(r, 500));
    }
  } catch {
    // Ne pas faire echouer la publication si le picker n'est pas trouve
  }
}
