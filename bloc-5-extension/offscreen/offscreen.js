// Offscreen document for DOM operations that can't run in the SW.
// Currently unused but required by the manifest declaration.
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.target !== "offscreen") return;
  sendResponse({ ok: true });
});
