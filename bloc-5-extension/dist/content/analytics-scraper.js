(() => {
  // content/analytics-scraper.js
  var LINKEDIN_SELECTORS = {
    likes: [
      'button[aria-label*="r\xE9action"] span.social-counts-reactions__count',
      'span[data-test="likes-count"]',
      "button.social-action-button__reaction-count span"
    ],
    comments: [
      'button[aria-label*="commentaire"] span',
      "li.social-details-social-counts__item--comments span"
    ],
    reposts: [
      'button[aria-label*="republication"] span',
      "li.social-details-social-counts__item--reposts span"
    ],
    views: [
      'span[data-impression-id*="views"]',
      "span.social-details-social-counts__reactions-count"
    ]
  };
  var INSTAGRAM_SELECTORS = {
    likes: [
      "section span span",
      'a[href*="liked_by"] span',
      "div._aacl span"
    ],
    comments: [
      "ul.Mr508 li span span"
    ]
  };
  function extractNumber(el) {
    if (!el) return 0;
    const text = el.textContent.replace(/\s/g, "").replace(/,/g, "").replace(/\./g, "");
    const n = parseInt(text, 10);
    return isNaN(n) ? 0 : n;
  }
  function trySelectors(selectors) {
    for (const sel of selectors) {
      try {
        const el = document.querySelector(sel);
        if (el) return extractNumber(el);
      } catch (_) {
      }
    }
    return 0;
  }
  function scrapeLinkedIn() {
    return {
      likes: trySelectors(LINKEDIN_SELECTORS.likes),
      comments: trySelectors(LINKEDIN_SELECTORS.comments),
      reposts: trySelectors(LINKEDIN_SELECTORS.reposts),
      views: trySelectors(LINKEDIN_SELECTORS.views)
    };
  }
  function scrapeInstagram() {
    return {
      likes: trySelectors(INSTAGRAM_SELECTORS.likes),
      comments: trySelectors(INSTAGRAM_SELECTORS.comments),
      reposts: 0,
      views: 0
    };
  }
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.action !== "scrapeAnalytics") return;
    const platform = message.platform;
    const metrics = platform === "instagram" ? scrapeInstagram() : scrapeLinkedIn();
    sendResponse(metrics);
    return true;
  });
})();
