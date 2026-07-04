(() => {
  // content/linkedin-publisher.js
  var _initialized = false;
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg.type !== "PUBLISH_POST") return;
    if (_initialized) return;
    _initialized = true;
    publishViaApi(msg.task).then((result) => sendResponse(result)).catch((err) => sendResponse({ status: "failed", error_code: "UNKNOWN", error_message: err.message }));
    return true;
  });
  function getCsrf() {
    const m = document.cookie.match(/JSESSIONID="?([^;"]+)"?/);
    return m ? m[1] : "";
  }
  function orgUrnFromPageUrl(pageUrl) {
    if (!pageUrl || !pageUrl.includes("/company/")) return null;
    const tail = pageUrl.split("/company/")[1].replace(/^\/+/, "");
    const id = tail.split("/")[0].split("?")[0];
    return /^\d+$/.test(id) ? `urn:li:organization:${id}` : null;
  }
  function findActivityUrn(data) {
    try {
      const blob = JSON.stringify(data);
      const m = blob.match(/urn:li:activity:(\d+)/);
      return m ? m[0] : null;
    } catch {
      return null;
    }
  }
  async function publishViaApi(task) {
    const csrf = getCsrf();
    if (!csrf) {
      return { status: "failed", error_code: "AUTH_REQUIRED", error_message: "JSESSIONID introuvable \u2014 reconnecte-toi \xE0 LinkedIn" };
    }
    const orgUrn = orgUrnFromPageUrl(task.page_url);
    let media = [];
    if (task.media_urls?.length) {
      try {
        const assetUrn = await uploadImage(task, csrf, orgUrn);
        if (assetUrn) {
          media = [{ category: "IMAGE", mediaUrn: assetUrn, tapTargets: [] }];
        }
      } catch (e) {
        console.warn("[LI] upload image \xE9chou\xE9:", e.message);
      }
    }
    const payload = {
      visibleToConnectionsOnly: false,
      externalAudienceProviders: [],
      commentaryV2: { text: task.text || "", attributes: [] },
      origin: "FEED",
      allowedCommentersScope: "ALL",
      postState: "PUBLISHED",
      media
    };
    if (orgUrn) payload.containerEntity = orgUrn;
    const r = await fetch("https://www.linkedin.com/voyager/api/contentcreation/normShares", {
      method: "POST",
      headers: {
        "csrf-token": csrf,
        "content-type": "application/json; charset=UTF-8",
        "accept": "application/vnd.linkedin.normalized+json+2.1",
        "x-restli-protocol-version": "2.0.0"
      },
      credentials: "include",
      body: JSON.stringify(payload)
    });
    if (r.status === 401 || r.status === 403) {
      return { status: "failed", error_code: "AUTH_REQUIRED", error_message: `HTTP ${r.status} (session LinkedIn expir\xE9e ?)` };
    }
    if (!r.ok) {
      const t = await r.text().catch(() => "");
      return { status: "failed", error_code: "PUBLISH_REJECTED", error_message: `HTTP ${r.status}: ${t.slice(0, 200)}` };
    }
    let postUrl = null;
    try {
      const data = await r.json();
      const urn = findActivityUrn(data);
      if (urn) postUrl = `https://www.linkedin.com/feed/update/${urn}/`;
    } catch {
    }
    return { status: "success", post_url: postUrl };
  }
  async function uploadImage(task, csrf, orgUrn) {
    const bytes = task.media_data?.[0]?.bytes;
    if (!bytes) return null;
    const owner = orgUrn || await currentMemberUrn();
    if (!owner) return null;
    const reg = await fetch("https://www.linkedin.com/voyager/api/voyagerVideoDashMediaUploadMetadata?action=upload", {
      method: "POST",
      headers: {
        "csrf-token": csrf,
        "content-type": "application/json; charset=UTF-8",
        "accept": "application/vnd.linkedin.normalized+json+2.1",
        "x-restli-protocol-version": "2.0.0"
      },
      credentials: "include",
      body: JSON.stringify({ mediaUploadType: "IMAGE_SHARING", fileSize: bytes.length, filename: `post_${task.post_id}.png` })
    });
    if (!reg.ok) throw new Error(`registerUpload HTTP ${reg.status}`);
    const regData = await reg.json();
    const value = regData?.data?.value || regData?.value || {};
    const uploadUrl = value.singleUploadUrl || value.uploadUrl;
    const mediaUrn = value.urn || value.mediaArtifact || value.image;
    if (!uploadUrl || !mediaUrn) throw new Error("registerUpload: url/urn manquants");
    const put = await fetch(uploadUrl, { method: "PUT", credentials: "include", body: new Uint8Array(bytes) });
    if (!put.ok && put.status !== 201) throw new Error(`PUT bytes HTTP ${put.status}`);
    return mediaUrn;
  }
  async function currentMemberUrn() {
    try {
      const r = await fetch("https://www.linkedin.com/voyager/api/me", {
        headers: { "accept": "application/vnd.linkedin.normalized+json+2.1", "x-restli-protocol-version": "2.0.0" },
        credentials: "include"
      });
      const d = await r.json();
      const urn = JSON.stringify(d).match(/urn:li:fsd_profile:([A-Za-z0-9_-]+)/) || JSON.stringify(d).match(/urn:li:member:(\d+)/);
      if (!urn) return null;
      return urn[0].includes("member") ? urn[0] : `urn:li:person:${urn[1]}`;
    } catch {
      return null;
    }
  }
})();
