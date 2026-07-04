import { waitForElement } from "./shared/wait-for-element.js";
import { typeText, humanClick, humanPause } from "./shared/human-typer.js";
import { uploadMediaFromUrl } from "./shared/media-uploader.js";
import { identityMatches } from "./shared/identity.js";

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

function findByText(selector, text) {
  const els = document.querySelectorAll(selector);
  return Array.from(els).find((el) => el.textContent.trim().includes(text)) || null;
}

// Cliquer un element par son contenu texte (boutons FR + EN)
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

// Snapshot DOM pour debug — liste tous les [contenteditable] et les boutons visibles
function domSnapshot() {
  const editables = [...document.querySelectorAll("[contenteditable]")].map((el) => {
    const cls = el.className ? el.className.toString().split(" ").slice(0, 3).join(".") : "";
    return `${el.tagName.toLowerCase()}${cls ? "." + cls : ""}[h=${el.offsetHeight},role=${el.getAttribute("role") || "-"},ph="${(el.getAttribute("data-placeholder") || "").substring(0, 20)}"]`;
  });
  const btns = [...document.querySelectorAll("button, [role='button']")]
    .filter((b) => b.offsetHeight > 0)
    .slice(0, 10)
    .map((b) => `"${b.textContent.trim().substring(0, 30)}"[aria="${b.getAttribute("aria-label") || ""}"]`);
  return `contenteditable=[${editables.join(" | ") || "none"}] buttons=[${btns.join(", ")}]`;
}

// Attendre l'editeur — itere sur la cascade de selecteurs remote (sel.text_editor),
// en filtrant les elements invisibles et ceux de la nav/header/search.
async function waitForEditor(editorSelectors, timeoutMs = 15_000) {
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
        } catch {}
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
    // Attendre que la page soit chargee
    await new Promise((r) => setTimeout(r, 3000));

    // Sur la page admin company (?share=true), le bouton "Créer un post" peut avoir besoin d'un clic
    const openTexts = ["créer un post", "commencer un post", "start a post", "create a post", "commencer", "créer", "share"];
    clickByText(openTexts);
    await new Promise((r) => setTimeout(r, 1500));

    // ----- ETAPE 1 : trouver l'editeur -----
    let editor = null;
    try {
      editor = await waitForEditor(sel.text_editor, 8_000);
    } catch {}

    if (!editor) {
      // Fallback : cliquer les boutons compose via les selecteurs remote
      const btn = await waitForElement(sel.btn_open_compose, { timeoutMs: 5_000 }).catch(() => null);
      if (btn) {
        await humanClick(btn);
        await new Promise((r) => setTimeout(r, 1500));
      } else {
        // Dernier essai par texte
        clickByText(openTexts);
        await new Promise((r) => setTimeout(r, 1500));
      }
      editor = await waitForEditor(sel.text_editor, 12_000);
    }

    // ----- ETAPE 2 : selectionner puis VERIFIER le compte entreprise -----
    if (task.publish_as_name) {
      const pickError = await selectPublishingIdentity(sel, task.publish_as_name);
      const identity = readPublishingIdentity(sel);
      if (!identityMatches(identity, task.publish_as_name)) {
        return {
          status: "failed",
          error_code: "WRONG_IDENTITY",
          error_message:
            `Compositeur en tant que '${identity || "inconnu"}' au lieu de '${task.publish_as_name}'` +
            (pickError ? ` (picker: ${pickError})` : ""),
        };
      }
    }

    // ----- ETAPE 3 : taper le texte -----
    await humanClick(editor);
    if (task.text) await typeText(editor, task.text);

    // ----- ETAPE 4 : uploader un media si besoin -----
    if (task.media_urls?.length > 0) {
      await humanPause();
      const fileInput = await waitForElement(sel.file_input, { timeoutMs: 5_000 });
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
    const submitBtn = await waitForElement(sel.btn_submit, { timeoutMs: 10_000 });
    await humanClick(submitBtn);

    // ----- ETAPE 6 : attendre la confirmation -----
    await waitForElement(sel.success_toast, { timeoutMs: 30_000 });

    return { status: "success", post_url: null };
  } catch (err) {
    const code = err.message.includes("not found") || err.message.includes("Editor not found")
      ? "SELECTOR_NOT_FOUND"
      : "UNKNOWN";
    return { status: "failed", error_code: code, error_message: err.message };
  }
}

// Lit le nom de l'acteur courant du compositeur (page ou profil).
function readPublishingIdentity(sel) {
  for (const s of sel.actor_name.split(",").map((x) => x.trim())) {
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

// Ouvre le picker d'identite et choisit la page par son nom.
// Retourne null si OK, ou un message d'erreur — l'echec n'est plus silencieux :
// c'est la verification d'identite en aval qui decide d'abort.
async function selectPublishingIdentity(sel, pageName) {
  try {
    // Deja la bonne identite (cas page admin) : rien a faire
    if (identityMatches(readPublishingIdentity(sel), pageName)) return null;

    const pickerBtn = await waitForElement(sel.identity_picker_trigger, { timeoutMs: 5_000 }).catch(() => null);
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
