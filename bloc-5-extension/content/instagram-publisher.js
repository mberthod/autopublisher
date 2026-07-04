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

// Cherche un bouton par son texte (Instagram rend ses boutons en div[role=button]
// generiques ; le texte est le seul discriminant fiable). Fallback sur le
// selecteur backend si aucun match texte.
async function clickButtonByText(texts, fallbackSel, timeoutMs = 10_000) {
  const deadline = Date.now() + timeoutMs;
  const needles = texts.map((t) => t.toLowerCase());
  while (Date.now() < deadline) {
    const candidates = document.querySelectorAll("div[role='button'], button, [role='button'] div");
    for (const el of candidates) {
      if (el.offsetHeight === 0) continue;
      const t = el.textContent.trim().toLowerCase();
      if (t && t.length < 20 && needles.some((n) => t === n || t.includes(n))) {
        await humanClick(el);
        return true;
      }
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  // Fallback selecteur backend
  if (fallbackSel) {
    const btn = await waitForElement(fallbackSel, { timeoutMs: 3_000 }).catch(() => null);
    if (btn) {
      await humanClick(btn);
      return true;
    }
  }
  return false;
}

// Cherche l'input file, en revelant le dialog si besoin (menu "Publication" puis
// bouton "Selectionner depuis l'ordinateur").
async function findFileInput(sel, timeoutMs = 15_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const input = document.querySelector(sel.file_input);
    if (input) return input;
    // Menu eventuel apres le "+" : choisir "Publication"
    await clickButtonByText(["publication", "post"], null, 500).catch(() => {});
    // Bouton pour ouvrir le selecteur de fichier
    await clickButtonByText(
      ["sélectionner depuis l'ordinateur", "select from computer", "sélectionner sur l'ordinateur", "selectionner"],
      null, 500
    ).catch(() => {});
    await new Promise((r) => setTimeout(r, 500));
  }
  return null;
}

// Liste les boutons/roles visibles pour diagnostiquer un blocage sans allers-retours
function domSnapshot() {
  const btns = [...document.querySelectorAll("button, [role='button'], a, [role='menuitem'], input[type='file']")]
    .filter((b) => b.offsetHeight > 0 || b.type === "file")
    .slice(0, 18)
    .map((b) => {
      const t = (b.textContent || "").trim().slice(0, 24);
      const al = b.getAttribute("aria-label") || "";
      const tag = b.tagName.toLowerCase() + (b.type ? `[${b.type}]` : "");
      return `${tag}"${t}"${al ? `(aria=${al.slice(0, 24)})` : ""}`;
    });
  return btns.join(" | ") || "aucun bouton visible";
}

async function publishInstagram(task, sel) {
  // Check logged in
  const navCheck = document.querySelector("nav, a[href='/']");
  if (!navCheck) {
    return { status: "failed", error_code: "AUTH_REQUIRED", error_message: "Not logged into Instagram" };
  }

  try {
    if (!task.media_urls?.length) {
      return { status: "failed", error_code: "UNKNOWN", error_message: "Instagram requires at least one image" };
    }

    // Click new post icon (le selecteur matche un <svg> → humanClick remonte au bouton)
    const newPostBtn = await waitForElement(sel.btn_new_post, { timeoutMs: 10_000 });
    await humanClick(newPostBtn);
    await humanPause();

    // File input : gere le sous-menu "Publication" + bouton "Selectionner..."
    const fileInput = await findFileInput(sel, 15_000);
    if (!fileInput) {
      return { status: "failed", error_code: "SELECTOR_NOT_FOUND", error_message: `Champ d'upload introuvable. DOM: ${domSnapshot()}` };
    }
    await uploadMediaFromUrl(fileInput, task.media_urls[0], `post_${task.post_id}.png`, task.media_data?.[0] ?? null);
    await humanPause();

    // Rogner → Suivant, puis Filtres/Modifier → Suivant (2 ecrans "Suivant")
    for (let i = 0; i < 2; i++) {
      const ok = await clickButtonByText(["suivant", "next"], sel.next_button, 12_000);
      if (!ok) return { status: "failed", error_code: "SELECTOR_NOT_FOUND", error_message: `Bouton 'Suivant' introuvable (etape ${i + 1}). DOM: ${domSnapshot()}` };
      await humanPause();
    }

    // Write caption
    if (task.text) {
      const caption = await waitForElement(sel.caption_editor, { timeoutMs: 10_000 }).catch(() => null);
      if (!caption) return { status: "failed", error_code: "SELECTOR_NOT_FOUND", error_message: `Champ legende introuvable. DOM: ${domSnapshot()}` };
      await humanClick(caption);
      await typeText(caption, task.text);
    }

    // Share / Partager
    await humanPause();
    const shared = await clickButtonByText(["partager", "share"], sel.share_button, 12_000);
    if (!shared) return { status: "failed", error_code: "SELECTOR_NOT_FOUND", error_message: `Bouton 'Partager' introuvable. DOM: ${domSnapshot()}` };

    // Confirmation reelle : sans indicateur de succes, ne pas marquer published
    const confirmed = await waitForElement(sel.success_indicator, { timeoutMs: 30_000 }).catch(() => null);
    if (!confirmed) {
      return {
        status: "failed",
        error_code: "PUBLISH_UNCONFIRMED",
        error_message: "No success indicator within 30s after clicking share",
      };
    }

    return { status: "success", post_url: null };
  } catch (err) {
    const code = err.message.includes("not found") ? "SELECTOR_NOT_FOUND" : "UNKNOWN";
    return { status: "failed", error_code: code, error_message: err.message };
  }
}

