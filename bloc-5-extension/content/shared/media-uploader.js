/**
 * Injects a media blob into a hidden <input type="file"> element.
 * Downloads the file from a URL, converts to Blob, uses DataTransfer.
 */
export async function uploadMediaFromUrl(fileInput, url, filename = "media.png") {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`media download failed: HTTP ${response.status}`);
  const blob = await response.blob();

  const file = new File([blob], filename, { type: blob.type || "image/png" });
  const dt = new DataTransfer();
  dt.items.add(file);
  fileInput.files = dt.files;
  fileInput.dispatchEvent(new Event("change", { bubbles: true }));
  fileInput.dispatchEvent(new Event("input", { bubbles: true }));
}
