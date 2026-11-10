// This exact function is injected only after the user invokes activeTab.
export function readPageContext() {
  // Defense in depth: LinkedIn is manual-only even if a caller forgets the outer guard.
  if (location.hostname === "linkedin.com" || location.hostname.endsWith(".linkedin.com")) {
    throw new Error("LinkedIn is manual-only; page content must not be read.");
  }
  return {
    source_url: location.href,
    source_title: document.title.slice(0, 500),
    quote: (window.getSelection()?.toString() || "").slice(0, 4000),
  };
}

export function isLinkedIn(url) {
  try {
    const host = new URL(url).hostname;
    return host === "linkedin.com" || host.endsWith(".linkedin.com");
  } catch { return false; }
}

export async function contextForTab(tab, readContext) {
  if (isLinkedIn(tab.url)) {
    return { source_url: tab.url, source_title: "", quote: "" };
  }
  return readContext(tab.id);
}
