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
  var CREATE_QUERY_ID = "voyagerContentcreationDashShares.80089eb2e82a2dfa23cb621fb09eb7bf";
  var CREATE_URL = `https://www.linkedin.com/voyager/api/graphql?action=execute&queryId=${CREATE_QUERY_ID}`;
  function getCsrf() {
    const m = document.cookie.match(/JSESSIONID="?([^;"]+)"?/);
    return m ? m[1] : "";
  }
  async function waitForLiHeaders(timeoutMs, needPageInstance) {
    const el = document.documentElement;
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const track = el.getAttribute("data-li-track");
      const pageInstance = el.getAttribute("data-li-page-instance");
      if (track && (!needPageInstance || pageInstance)) {
        return { track, pageInstance, lang: el.getAttribute("data-li-lang") };
      }
      await new Promise((r) => setTimeout(r, 300));
    }
    return {
      track: el.getAttribute("data-li-track"),
      pageInstance: el.getAttribute("data-li-page-instance"),
      lang: el.getAttribute("data-li-lang")
    };
  }
  function orgIdFromPageUrl(pageUrl) {
    if (!pageUrl || !pageUrl.includes("/company/")) return null;
    const id = pageUrl.split("/company/")[1].replace(/^\/+/, "").split("/")[0].split("?")[0];
    return /^\d+$/.test(id) ? id : null;
  }
  function findActivityUrn(data) {
    try {
      const m = JSON.stringify(data).match(/urn:li:(?:activity|share|ugcPost):(\d+)/);
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
    const orgId = orgIdFromPageUrl(task.page_url);
    const post = {
      allowedCommentersScope: "ALL",
      intendedShareLifeCycleState: "PUBLISHED",
      origin: orgId ? "ORGANIZATION" : "FEED",
      visibilityDataUnion: { visibilityType: "ANYONE" },
      commentary: { text: task.text || "", attributesV2: [] }
    };
    if (orgId) post.nonMemberActorUrn = `urn:li:fsd_company:${orgId}`;
    if (task.media_urls?.length) {
      try {
        const mediaUrn = await uploadImage(task, csrf, orgId);
        if (mediaUrn) {
          post.media = { category: "IMAGE", mediaUrn, tapTargets: [], altText: "" };
        }
      } catch (e) {
        console.warn("[LI] upload image \xE9chou\xE9, publication en texte:", e.message);
      }
    }
    const body = { variables: { post }, queryId: CREATE_QUERY_ID, includeWebMetadata: true };
    const li = await waitForLiHeaders(12e3, !!orgId);
    const headers = {
      "csrf-token": csrf,
      "content-type": "application/json; charset=UTF-8",
      "accept": "application/vnd.linkedin.normalized+json+2.1",
      "x-restli-protocol-version": "2.0.0",
      "x-li-lang": li.lang || "fr_FR"
    };
    if (li.track) headers["x-li-track"] = li.track;
    if (li.pageInstance) headers["x-li-page-instance"] = li.pageInstance;
    const r = await fetch(CREATE_URL, {
      method: "POST",
      headers,
      credentials: "include",
      body: JSON.stringify(body)
    });
    if (r.status === 401 || r.status === 403) {
      return { status: "failed", error_code: "AUTH_REQUIRED", error_message: `HTTP ${r.status} (session LinkedIn expir\xE9e ?)` };
    }
    const raw = await r.text().catch(() => "");
    if (!r.ok) {
      return { status: "failed", error_code: "PUBLISH_REJECTED", error_message: `HTTP ${r.status}: ${raw.slice(0, 250)}` };
    }
    if (/createContentcreationDashShares":null|"exceptionClass"|FORBIDDEN|serviceErrorCode/i.test(raw)) {
      return { status: "failed", error_code: "PUBLISH_REJECTED", error_message: `R\xE9ponse LinkedIn: ${raw.slice(0, 1500)}` };
    }
    let postUrl = null;
    try {
      const urn = findActivityUrn(JSON.parse(raw));
      if (urn) postUrl = `https://www.linkedin.com/feed/update/${urn}/`;
    } catch {
    }
    return { status: "success", post_url: postUrl };
  }
  async function uploadImage(task, csrf, orgId) {
    const bytes = task.media_data?.[0]?.bytes;
    if (!bytes) return null;
    const owner = orgId ? `urn:li:fsd_company:${orgId}` : null;
    const reg = await fetch("https://www.linkedin.com/voyager/api/voyagerVideoDashMediaUploadMetadata?action=upload", {
      method: "POST",
      headers: {
        "csrf-token": csrf,
        "content-type": "application/json; charset=UTF-8",
        "accept": "application/vnd.linkedin.normalized+json+2.1",
        "x-restli-protocol-version": "2.0.0"
      },
      credentials: "include",
      body: JSON.stringify({ mediaUploadType: "IMAGE_SHARING", fileSize: bytes.length, ...owner ? { organizationActor: owner } : {} })
    });
    if (!reg.ok) throw new Error(`registerUpload HTTP ${reg.status}`);
    const regData = await reg.json();
    const value = regData?.data?.value || regData?.value || {};
    const uploadUrl = value.singleUploadUrl || value.uploadUrl;
    const mediaUrn = value.urn || value.image || value.mediaArtifact;
    if (!uploadUrl || !mediaUrn) throw new Error("registerUpload: url/urn manquants");
    const put = await fetch(uploadUrl, { method: "PUT", credentials: "include", body: new Uint8Array(bytes) });
    if (!put.ok && put.status !== 201) throw new Error(`PUT bytes HTTP ${put.status}`);
    return mediaUrn;
  }
})();
