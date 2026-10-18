// Service worker: does the API call so it isn't blocked by the page's CSP,
// and toggles the panel when the toolbar icon is clicked.

const API_BASE = "http://127.0.0.1:8000";

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "tutor") {
    fetch(`${API_BASE}/tutor`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(msg.payload),
    })
      .then(async (r) => {
        if (!r.ok) {
          const text = await r.text();
          throw new Error(`API ${r.status}: ${text}`);
        }
        return r.json();
      })
      .then((data) => sendResponse({ ok: true, answer: data.answer }))
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true; // keep the message channel open for the async response
  }
});

// Clicking the toolbar icon toggles the in-page panel.
chrome.action.onClicked.addListener((tab) => {
  if (tab.id != null) chrome.tabs.sendMessage(tab.id, { type: "toggle" });
});