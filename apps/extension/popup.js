import { contextForTab, isLinkedIn, readPageContext } from "./capture.js";

const el = id => document.getElementById(id);
const ids = ["source_url", "person", "company", "channel", "action", "notes", "followup_on"];
let config = {};
let session = null;
let draft = null;
let inFlight = false;
const params = new URLSearchParams(location.search);
const floating = params.get("floating") === "1";
let collapsed = false;
let expandedSize = { width: 420, height: 720 };
if (floating) {
  document.documentElement.classList.add("floating-window");
  document.body.classList.add("floating");
  el("detach").hidden = true; el("collapse").hidden = false; el("hide").hidden = false;
  el("hide-setting").hidden = false;
}
el("extension-id").value = chrome.runtime.id;

function fail(error) { el("error").textContent = error.message; el("error").hidden = false; }
function clearError() { el("error").hidden = true; }
async function request(path, method = "GET", body) {
  if (!["http://127.0.0.1:8000", "http://127.0.0.1:8001"].includes(config.api)) throw new Error("Choose a local API and save pairing first.");
  let response;
  try {
    response = await fetch(config.api + "/api" + path, {
      method, credentials: "omit", headers: { Authorization: `Bearer ${config.token}`, "Content-Type": "application/json", "X-Extension-ID": chrome.runtime.id },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch { throw new Error("Cannot reach the local API. Start the server and retry; your draft is kept."); }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : data.detail?.message || "Invalid capture. Check the URL and field lengths.");
  return data;
}
function modeNotice(url) {
  el("mode-notice").hidden = !isLinkedIn(url);
  el("mode-notice").textContent = "LinkedIn · manual logging only. No HTML, profile text, page title or selected text is read. Enter your own notes; this is not a LinkedIn-approved integration.";
}
function showDraft() {
  if (draft) {
    const d = draft.details;
    d.notes = (d.notes + (d.quote && !d.notes.includes(d.quote) ? `\n\n${d.quote}` : "")).trim();
    d.quote = "";
  }
  for (const id of ids) el(id).value = draft?.details[id] || "";
  modeNotice(draft?.details.source_url);
}
async function sourceTab() {
  if (floating) {
    const [tab] = await chrome.tabs.query({ active: true, windowId: Number(params.get("sourceWindow")) });
    return tab;
  }
  return (await chrome.tabs.query({ active: true, currentWindow: true }))[0];
}
async function readTab() {
  const tab = await sourceTab();
  try {
    if (!tab?.id) throw new Error("No tab");
    const context = await contextForTab(tab, async tabId => {
      const [result] = await chrome.scripting.executeScript({ target: { tabId }, func: readPageContext });
      return result.result;
    });
    const host = new URL(context.source_url).hostname;
    const channel = host === "linkedin.com" || host.endsWith(".linkedin.com") ? "linkedin" : host === "x.com" ? "x" : "web";
    draft = { sessionId: session.id, request_id: crypto.randomUUID(), details: { ...context, person: "", company: "", channel, action: "researched", notes: "", followup_on: null, occurred_at: new Date().toISOString() } };
    await chrome.storage.local.set({ draft });
    showDraft();
  } catch {
    throw new Error("Open a normal website, then click the extension toolbar button again. Restricted pages cannot be read. Manual capture is also available in the app.");
  }
}
async function refresh() {
  clearError(); el("capture-form").hidden = true;
  try {
    ({ config = {}, draft = null } = await chrome.storage.local.get(["config", "draft"]));
    el("hide-after-save").checked = !!config.hideAfterSave;
    el("api").value = config.api || "http://127.0.0.1:8000";
    if (!config.token) { el("settings").open = true; el("session").textContent = "Pair your browser, then start a session in the app."; return; }
    session = (await request("/extension/session")).session;
    el("session").textContent = session ? `${session.workflow_name || session.intention} / ${session.run_name || "Current run"} · ${session.state}` : "Start a run in the app, then refresh here.";
    if (session?.state !== "active") return;
    if (draft && draft.sessionId !== session.id) {
      el("status").textContent = "A draft from an earlier session is still on this browser. Start a new page capture to replace it.";
      el("capture-form").hidden = false; showDraft(); el("capture-submit").disabled = true; return;
    }
    el("capture-form").hidden = false; el("capture-submit").disabled = false;
    if (draft) { showDraft(); el("status").textContent = "Restored your unsent draft. Capture again safely if a previous request was interrupted."; }
    else await readTab();
  } catch (error) { fail(error); }
}
el("pair-form").addEventListener("submit", async event => {
  event.preventDefault(); clearError();
  config = { ...config, api: el("api").value, token: el("token").value.trim() };
  try {
    await request("/extension/session"); await chrome.storage.local.set({ config });
    el("token").value = ""; el("settings").open = false; el("status").textContent = "Pairing saved."; await refresh();
  } catch (error) { fail(error); }
});
el("forget").addEventListener("click", async () => {
  await chrome.storage.local.remove(["config", "draft"]); config = {}; draft = null;
  el("status").textContent = "Local pairing and draft forgotten. Revoke server access in the app.";
  await refresh();
});
el("capture-form").addEventListener("input", async () => {
  if (!draft || inFlight) return;
  for (const id of ids) draft.details[id] = el(id).value;
  modeNotice(draft.details.source_url);
  draft.details.followup_on ||= null;
  await chrome.storage.local.set({ draft });
});
el("capture-form").addEventListener("submit", async event => {
  event.preventDefault(); if (!draft || !session || inFlight || draft.sessionId !== session.id) return;
  inFlight = true; clearError(); el("capture-submit").disabled = true;
  // Persist before transmitting; retry reuses the same ID and cannot create duplicate activity.
  try {
    for (const id of ids) draft.details[id] = el(id).value;
    draft.details.followup_on ||= null;
    await chrome.storage.local.set({ draft });
    await request(`/extension/sessions/${session.id}/captures`, "POST", { request_id: draft.request_id, details: draft.details });
    await chrome.storage.local.remove("draft"); draft = null;
    el("capture-form").hidden = true; el("status").textContent = "Captured for review. Finish your session in the app to approve it.";
    if (floating && config.hideAfterSave) await chrome.windows.update((await chrome.windows.getCurrent()).id, { state: "minimized" });
  } catch (error) { fail(error); } finally { inFlight = false; el("capture-submit").disabled = false; }
});
el("new-page").addEventListener("click", async () => {
  clearError(); if (inFlight) return;
  try { await readTab(); el("capture-submit").disabled = false; el("status").textContent = "Current page ready for capture."; } catch (error) { fail(error); }
});
el("retry").addEventListener("click", refresh);
el("detach").addEventListener("click", async () => {
  try {
    const tab = await sourceTab();
    if (!tab?.id) throw new Error("Open capture from the browser toolbar on your source page.");
    const response = await chrome.runtime.sendMessage({ type: "open-capture-window", sourceTabId: tab.id, sourceWindowId: tab.windowId });
    if (response?.error) throw new Error(response.error);
    window.close();
  } catch (error) { fail(error); }
});
el("collapse").addEventListener("click", async () => {
  clearError();
  try {
    const win = await chrome.windows.getCurrent();
    if (!collapsed) expandedSize = { width: win.width, height: win.height };
    const nextCollapsed = !collapsed;
    const requested = nextCollapsed ? { width: 340, height: 155 } : expandedSize;
    const width = Math.min(requested.width, screen.availWidth);
    const height = Math.min(requested.height, screen.availHeight);
    // Shrinking can leave a previously legal window mostly offscreen. Keep the new
    // bounds within this display's work area, including displays left of the main one.
    const left = Math.max(screen.availLeft, Math.min(win.left, screen.availLeft + screen.availWidth - width));
    const top = Math.max(screen.availTop, Math.min(win.top, screen.availTop + screen.availHeight - height));
    await chrome.windows.update(win.id, { width, height, left, top });
    collapsed = nextCollapsed; document.body.classList.toggle("collapsed", collapsed);
    el("collapse").textContent = collapsed ? "Expand" : "Collapse";
  } catch (error) { fail(error); }
});
el("hide").addEventListener("click", async () => {
  try { await chrome.windows.update((await chrome.windows.getCurrent()).id, { state: "minimized" }); }
  catch (error) { fail(error); }
});
el("hide-after-save").addEventListener("change", async () => {
  config.hideAfterSave = el("hide-after-save").checked; await chrome.storage.local.set({ config });
});
await refresh();
