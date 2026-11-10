// No browsing listeners: the toolbar click/shortcut is the only capture trigger.
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.setAccessLevel({ accessLevel: "TRUSTED_CONTEXTS" });
});

// A separate browser-owned window, never an overlay injected into a website.
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if (sender.id !== chrome.runtime.id || message.type !== "open-capture-window") return;
  (async () => {
    try {
      const source = await chrome.windows.get(message.sourceWindowId);
      const url = new URL(chrome.runtime.getURL("popup.html"));
      url.searchParams.set("floating", "1");
      url.searchParams.set("tab", String(message.sourceTabId));
      url.searchParams.set("sourceWindow", String(message.sourceWindowId));
      const window = await chrome.windows.create({
        url: url.href, type: "popup", width: 420, height: 720, focused: true,
        left: Math.max(0, (source.left || 0) + 30), top: Math.max(0, (source.top || 0) + 100),
      });
      respond({ id: window.id });
    } catch { respond({ error: "Could not open a capture window. Keep using the toolbar popup." }); }
  })();
  return true;
});
