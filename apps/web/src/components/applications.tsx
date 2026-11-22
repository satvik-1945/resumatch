"use client";
import { useEffect, useState } from "react";
import { api, type EmailOverview, type ScanResult } from "@/lib/api";

const oauthNotices: Record<string, string> = {
  connected: "Gmail connected. Scan your inbox whenever you like.",
  denied: "Gmail access was not granted. Nothing was connected.",
  expired: "That sign-in link expired. Try Connect Gmail again.",
  scope: "Read-only Gmail access is required. Try again and tick the Gmail permission.",
  error: "Google sign-in failed. Try again.",
};
const ago = (at: string | null) => at ? new Date(at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "never";

// Applications found in connected inboxes. Scans only run when you press the button.
export function Applications({ revision, onReview }: { revision: string; onReview: (runId: string) => void }) {
  const [overview, setOverview] = useState<EmailOverview | null>(null);
  const [scan, setScan] = useState<ScanResult | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [removing, setRemoving] = useState<string | null>(null);
  const [notice] = useState(() => oauthNotices[new URLSearchParams(location.search).get("email") ?? ""] ?? "");
  const [reloads, setReloads] = useState(0);
  useEffect(() => {
    // Drop ?view=…&email=… from the address bar once read.
    if (location.search) history.replaceState(null, "", location.pathname);
  }, []);
  useEffect(() => {
    api<EmailOverview>("/email").then(setOverview, e => setError((e as Error).message));
  }, [revision, reloads]);
  async function work(label: string, task: () => Promise<void>) {
    setBusy(label); setError("");
    try { await task(); } catch (e) { setError((e as Error).message); } finally { setBusy(""); }
  }
  const connect = () => work("Opening Google…", async () => { location.href = (await api<{ url: string }>("/email/connect", "POST")).url; });
  const runScan = () => work("Scanning your inboxes… this can take a minute or two.", async () => { const result = await api<ScanResult>("/email/scan", "POST"); setScan(result); setOverview(result); });
  const remove = (id: string) => work("Disconnecting…", async () => { await api(`/email/accounts/${id}`, "DELETE"); setRemoving(null); setReloads(n => n + 1); });
  const c = overview?.counts;
  const toReview = c ? c.applied_to_review + c.responses_to_review : 0;
  return <>
    <header className="section-title"><p className="eyebrow">EVERY APPLICATION COUNTS</p><h1>Applications</h1><p className="lede">Scan your inbox each morning. “Thanks for applying” emails become applications; replies from companies light up amber until you answer.</p></header>
    {notice && <p className="success" role="status">{notice}</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {!overview ? <section className="panel" role="status">Loading applications…</section> : <>
      <div className="app-stats">
        <section><p>APPLIED</p><strong>{c!.applied}</strong>{c!.applied_to_review > 0 && <small>+{c!.applied_to_review} to review</small>}</section>
        <section><p>THIS WEEK</p><strong>{c!.applied_this_week}</strong><small>approved applications</small></section>
        <section><p>REPLIES</p><strong>{c!.responses}</strong>{c!.responses_to_review > 0 && <small>+{c!.responses_to_review} to review</small>}</section>
        <section className={c!.needs_reply ? "amber" : ""}><p>NEED YOUR REPLY</p><strong>{c!.needs_reply}</strong><small>{c!.needs_reply ? "a company is waiting on you" : "all caught up"}</small></section>
      </div>
      <section className="panel scan-panel">
        <div className="panel-heading"><div><h2>Morning scan</h2><p className="muted">Reads only likely job emails: sender, subject and a short preview. Bodies are never downloaded.</p></div>
          <button className="primary" disabled={!!busy || !overview.accounts.length || !overview.configured} onClick={() => void runScan()}>{busy.startsWith("Scanning") ? "Scanning…" : "Scan inbox"}</button></div>
        {busy && <p className="hint" role="status">{busy}</p>}
        {scan && <p className="scan-result" role="status">Checked {scan.scanned} new email{scan.scanned === 1 ? "" : "s"}: <strong>{scan.applications}</strong> application{scan.applications === 1 ? "" : "s"}, <strong>{scan.responses}</strong> repl{scan.responses === 1 ? "y" : "ies"}, {scan.ignored} not about a job{scan.viewed ? `, ${scan.viewed} “application viewed” notice${scan.viewed === 1 ? "" : "s"}` : ""}{scan.duplicates ? `, ${scan.duplicates} repeat${scan.duplicates === 1 ? "" : "s"} of the same thread` : ""}.</p>}
        {scan?.warnings.map(w => <p className="notice" key={w}>{w}</p>)}
        {overview.open_run_id && toReview > 0 && <button className="secondary review-cta" onClick={() => onReview(overview.open_run_id!)}>Review {toReview} new record{toReview === 1 ? "" : "s"} →</button>}
        {overview.open_run_id && toReview === 0 && <button className="text-button" onClick={() => onReview(overview.open_run_id!)}>Open the review run to complete it</button>}
      </section>
      {!!overview.recent_responses.length && <section className="panel"><h2>Replies</h2>
        {overview.recent_responses.map(r => <div className={`list-row reply-row ${r.needs_reply ? "amber" : ""}`} key={r.id}>
          <div><strong>{r.company || r.person || "Company reply"}</strong><p className="hint">{r.subject}</p><p className="hint">{new Date(r.received_at).toLocaleDateString()} · {r.decision === "pending" ? "waiting for review" : r.needs_reply ? "needs your reply" : "no action needed"}</p></div>
          <a href={r.source_url} target="_blank" rel="noreferrer">Open email ↗</a></div>)}
        <p className="hint">Mark a reply as handled with “Clear reminder” on Today once you’ve answered.</p></section>}
      <section className="panel">
        <div className="panel-heading"><h2>Connected inboxes</h2>{overview.configured && <button className="secondary" disabled={!!busy} onClick={() => void connect()}>+ Connect Gmail</button>}</div>
        {!overview.configured && <div className="notice"><p><strong>Gmail isn’t set up on this server yet.</strong></p><p>Add <code>GOOGLE_CLIENT_ID</code>, <code>GOOGLE_CLIENT_SECRET</code> and <code>EMAIL_TOKEN_KEY</code> to <code>.env</code> and restart the API. The setup guide lists the steps.</p></div>}
        {overview.configured && !overview.accounts.length && <p className="muted">No inbox connected. Connect one or more Gmail accounts; access is read-only and you can disconnect any time.</p>}
        {overview.accounts.map(a => <div className="list-row" key={a.id}>
          <div><strong>{a.email}</strong><p className="hint">Last scanned {ago(a.last_scanned_at)}</p>{a.last_error && <p className="error">{a.last_error}</p>}</div>
          {removing === a.id ? <span className="button-row"><button className="secondary" disabled={!!busy} onClick={() => void remove(a.id)}>Yes, disconnect</button><button className="text-button" onClick={() => setRemoving(null)}>Cancel</button></span>
            : <button className="text-button" onClick={() => setRemoving(a.id)}>Disconnect</button>}
        </div>)}
        <p className="hint">Disconnecting revokes Resumatch’s Google access. Records already approved stay in your history.</p>
      </section>
    </>}
  </>;
}
