"use client";
import { useState } from "react";
import { AiFeedback } from "@/components/ai-feedback";
import { actionLabels, api, type ContactLookup } from "@/lib/api";

// Cross-workflow check plus website-grounded talking points for a note the user handwrites.
// A brief is research help only; it is never logged as a sent message or activity.
export function ContactBrief({ url, onOpenAbout }: { url: string; onOpenAbout: () => void }) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<ContactLookup | null>(null);
  const [companyUrl, setCompanyUrl] = useState("");
  const [context, setContext] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  async function work(label: string, task: () => Promise<void>) {
    setBusy(label); setError(""); setNotice("");
    try { await task(); } catch (e) { setError((e as Error).message); } finally { setBusy(""); }
  }
  const load = () => work("Checking your records…", async () => {
    const found = await api<ContactLookup>(`/contacts/lookup?url=${encodeURIComponent(url)}`);
    setData(found); setCompanyUrl(previous => previous || found.brief?.company_url || ""); setContext(previous => previous || found.brief?.context || "");
  });
  if (!open) return <button className="text-button" onClick={() => { setOpen(true); void load(); }}>Check records & message brief</button>;
  const saved = data?.brief;
  const sections: [string, string[]][] = saved ? [
    ["What they do · from their site", saved.research.facts.map(f => f.fact)], ["Hook", saved.brief.hooks],
    ["Your credential", saved.brief.credentials], ["Bridge", saved.brief.bridges], ["Soft ask", saved.brief.asks], ["Avoid", saved.brief.avoid],
  ] : [];
  const copyText = sections.filter(([, items]) => items.length).map(([title, items]) => [title, ...items.map(i => `- ${i}`)].join("\n")).join("\n\n");
  return <section className="contact-brief" aria-label="Contact check and message brief">
    <div className="panel-heading"><h3>{!data ? "Checking…" : data.found ? `✓ Already in your records · ${data.records.length}` : "Not in your records yet"}</h3><button className="text-button" disabled={!!busy} onClick={() => setOpen(false)}>Close</button></div>
    {error && <p className="error" role="alert">{error}</p>}
    {busy && <p className="hint" role="status">{busy}</p>}
    {data?.found && <><p><strong>{[data.contact.person, data.contact.company].filter(Boolean).join(" · ") || "Name not recorded"}</strong></p>
      <div className="field-chips">{data.contact.fields.slice(0, 6).map(f => <span key={f.label}><strong>{f.label}:</strong> {String(f.value)}</span>)}</div>
      <ul className="brief-runs">{data.records.map(r => <li key={r.capture_id}>{r.workflow_name} · {r.run_name} · {actionLabels[r.action]} · {r.decision}</li>)}</ul></>}
    {data?.found && !data.about_me_set && <p className="notice">Briefs pick your credential from your resume. <button className="text-button" onClick={onOpenAbout}>Add your resume under About you</button> first.</p>}
    {data?.found && <form className="brief-form" onSubmit={e => { e.preventDefault(); void work("Researching their site & writing talking points…", async () => { setData(await api<ContactLookup>("/contacts/brief", "POST", { url, company_url: companyUrl.trim() || null, context })); setNotice("Brief ready. Write the note in your own words, then log what you sent."); }); }}>
      <label>Company website <span className="pill premium">Premium · research</span><input type="url" aria-label="Company website" maxLength={2000} value={companyUrl} onChange={e => setCompanyUrl(e.target.value)} placeholder="https://company.com (optional)" /></label>
      <label>What you know & your goal<span className="optional">Anything you found while reaching out: a post, shared ground, why them. And what you want from this note.</span><textarea aria-label="What you know & your goal" rows={3} maxLength={2000} value={context} onChange={e => setContext(e.target.value)} placeholder="e.g. Posted about hiring their first backend engineer. We both did hackathons. Goal: a 15-min intro chat." /></label>
      <button className="primary" disabled={!!busy || !data.about_me_set}>{saved ? "Regenerate message brief" : "Generate message brief"}</button>
      <p className="hint">Reads only the company’s own public site (homepage + /about), never LinkedIn. Company facts must quote the site or they’re dropped. Nothing is sent or logged.</p></form>}
    {notice && <p className="hint" role="status">{notice}</p>}
    {saved && <div className="brief-output">{sections.filter(([, items]) => items.length).map(([title, items]) => <div key={title}><h4>{title}</h4><ul>{items.map(i => <li key={i}>{i}</li>)}</ul></div>)}
      {!!saved.research.pages.length && <p className="hint">Sources: {saved.research.pages.map(p => <a key={p} href={p} target="_blank" rel="noreferrer">{p} </a>)}</p>}
      {!!saved.research.dropped_facts && <p className="hint">{saved.research.dropped_facts} company claim(s) dropped: not found on the site.</p>}
      {saved.brief.reference_draft && <details><summary>Reference draft · rewrite it in your own words</summary><blockquote>{saved.brief.reference_draft}</blockquote></details>}
      {saved.research.ai_run_id && <AiFeedback key={saved.research.ai_run_id} runId={saved.research.ai_run_id} />}
      <button className="secondary" onClick={() => void navigator.clipboard.writeText(copyText).then(() => setNotice("Talking points copied."), e => setError((e as Error).message))}>Copy talking points</button></div>}
  </section>;
}
