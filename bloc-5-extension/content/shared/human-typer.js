/**
 * Simulates human typing into a contenteditable or input element.
 * Types char by char with random delays between 50-150ms per char.
 * Adds random pauses of 1-3s between major actions.
 */

function randomBetween(min, max) {
  return min + Math.random() * (max - min);
}

export async function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

export async function humanPause() {
  await sleep(randomBetween(1000, 3000));
}

export async function typeText(element, text) {
  element.focus();
  for (const char of text) {
    // Use input event for contenteditable, value for input/textarea
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

export async function humanClick(element) {
  await humanPause();
  // Le selecteur peut matcher une icone <svg>/<span> non cliquable : remonter
  // au conteneur interactif reel (bouton/lien) qui porte le handler.
  const target =
    element.closest?.('button, a, [role="button"], [role="menuitem"], [role="tab"], label, [tabindex]') ||
    element;
  target.scrollIntoView({ behavior: "smooth", block: "center" });
  await sleep(randomBetween(300, 600));
  const opts = { bubbles: true, cancelable: true, view: window };
  target.dispatchEvent(new MouseEvent("mouseover", opts));
  await sleep(randomBetween(100, 300));
  target.dispatchEvent(new MouseEvent("mousedown", opts));
  await sleep(randomBetween(50, 150));
  target.dispatchEvent(new MouseEvent("mouseup", opts));
  // MouseEvent('click') fonctionne sur tout Element (y compris SVG), contrairement
  // a HTMLElement.click() qui n'existe pas sur les SVG.
  target.dispatchEvent(new MouseEvent("click", opts));
  if (typeof target.click === "function") {
    try { target.click(); } catch {}
  }
  await sleep(randomBetween(300, 600));
}
