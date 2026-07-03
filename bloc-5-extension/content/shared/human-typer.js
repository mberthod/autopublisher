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
