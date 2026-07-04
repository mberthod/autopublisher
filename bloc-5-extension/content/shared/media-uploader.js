/**
 * Injects a media blob into a hidden <input type="file"> element.
 * If mediaData (pre-fetched bytes) is provided, uses those directly.
 * Otherwise downloads from url (only works if CORS/PNA allows it).
 */
export async function uploadMediaFromUrl(fileInput, url, filename = "media.png", mediaData = null) {
  let blob;
  if (mediaData) {
    blob = new Blob([new Uint8Array(mediaData.bytes)], { type: mediaData.type || "image/png" });
    filename = mediaData.name || filename;
  } else {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`media download failed: HTTP ${response.status}`);
    blob = await response.blob();
  }

  const file = new File([blob], filename, { type: blob.type || "image/png" });
  const dt = new DataTransfer();
  dt.items.add(file);
  fileInput.files = dt.files;
  fileInput.dispatchEvent(new Event("change", { bubbles: true }));
  fileInput.dispatchEvent(new Event("input", { bubbles: true }));
}
