"use client";
import { useEffect, useState, type FormEvent } from "react";
import { api } from "@/lib/api";
type Pairing = { id: string; extension_id: string; expires_at: string; revoked: boolean };
export function PairBrowser() {
  const [items, setItems] = useState<Pairing[]>([]);
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  useEffect(() => { api<Pairing[]>("/pairings").then(setItems).catch(e => setError(e.message)); }, []);
  async function pair(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setCopied(false); setToken("");
    const extension_id = new FormData(event.currentTarget).get("extension_id");
    try { const data = await api<{ token: string }>("/pairings", "POST", { extension_id }); setToken(data.token); setItems(await api("/pairings")); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <><header className="section-title"><p className="eyebrow">YOUR BROWSER, ONE QUICK CAPTURE</p><h1>Less admin.<br />More connection.</h1><p className="lede">Save a page and selected text while you work. Your browser only reads a page when you ask it to.</p></header>
    <section className="panel"><h2>Connect the capture extension</h2><ol className="instructions"><li>Open <strong>chrome://extensions</strong> and enable Developer mode.</li><li>Choose <strong>Load unpacked</strong>, then select this repository’s <code>apps/extension</code> directory.</li><li>Pin <strong>Outreach capture</strong>. Open its popup and copy the Extension ID.</li><li>Paste that ID below, generate a pairing token, and paste the token into the extension.</li></ol>
      <p className="hint">Local Chrome/Chromium first. Pairing lasts 7 days and permits capture into your active session only. It cannot approve records or read your history.</p>
      {error && <p role="alert" className="error">{error}</p>}
      <form onSubmit={pair}><label>Extension ID<input name="extension_id" required pattern="[a-p]{32}" minLength={32} maxLength={32} placeholder="32-letter ID from the extension" /></label><button className="primary" disabled={busy}>{busy ? "Pairing…" : "Generate pairing token"}</button></form>
      {token && <div className="pair-secret"><label>Pairing token — shown once<input readOnly value={token} /></label><button className="secondary" onClick={async () => { try { await navigator.clipboard.writeText(token); setCopied(true); } catch { setError("Copy the token from the field above."); } }}>{copied ? "Copied" : "Copy token"}</button><p className="hint">Paste into your extension, then hide this token.</p><button className="text-button" onClick={() => setToken("")}>Hide token</button></div>}
    </section><section className="panel"><h2>Your browser pairings</h2>{!items.length && <p className="muted">No browser paired yet. Manual capture is ready whenever you are.</p>}{items.map(p => <div className="list-row" key={p.id}><div><code>{p.extension_id}</code><p className="hint">{p.revoked ? "Revoked" : `Expires ${new Date(p.expires_at).toLocaleDateString()}`}</p></div><button className="secondary" disabled={busy || p.revoked} onClick={async () => { setBusy(true); try { await api(`/pairings/${p.id}`, "DELETE"); setItems(await api("/pairings")); } catch (e) { setError((e as Error).message); } finally { setBusy(false); } }}>Revoke</button></div>)}</section>
    <aside className="notice"><strong>Prefer a movable panel?</strong> Reload extension v0.2.0, then choose <strong>Open movable window</strong> in its toolbar popup. Drag the native title bar to either side; collapse or hide it as needed. LinkedIn uses manual logging only—no LinkedIn HTML/title/selection reads. This is not a LinkedIn-approved integration. No automatic sending or inbox monitoring.</aside>
  </>;
}
