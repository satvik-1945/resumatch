"use client";
import { useState } from "react";
import { actionLabels, api, type ContactLookup } from "@/lib/api";

// Cross-workflow check plus website-grounded talking points for a note the user handwrites.
// A brief is research help only; it is never logged as a sent message or activity.
export function ContactBrief({ url }: { url: string }) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<ContactLookup | null>(null);
  const [about, setAbout] = useState("");
  const [aboutOpen, setAboutOpen] = useState(false);
  const [companyUrl, setCompanyUrl] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  async function work(label: string, task: () => Promise<void>) {
    setBusy(label); setError(""); setNotice("");
    try { await task(); } catch (e) { setError((e as Error).message); } finally { setBusy(""); }
  }
  const load = () => work("Checking your records…", async () => {
    const [found, profile] = await Promise.all([
      api<ContactLookup>(`/contacts/lookup?url=${encodeURIComponent(url)}`), api<{ about_me: string }>("/profile"),
    ]);
    setData(found); setAbout(profile.about_me); setAboutOpen(!profile.about_me.trim()); setCompanyUrl(previous => previous || found.brief?.company_url || "");
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
    {data && <details open={aboutOpen} onToggle={e => setAboutOpen(e.currentTarget.open)}><summary>About you {about.trim() ? "· used for credentials" : "· add this first"}</summary>
      <form onSubmit={e => { e.preventDefault(); void work("Saving…", async () => { setAbout((await api<{ about_me: string }>("/profile", "PUT", { about_me: about })).about_me); setNotice("About you saved."); }); }}>
        <label>Your background<textarea aria-label="About you" rows={4} maxLength={3000} value={about} onChange={e => setAbout(e.target.value)} placeholder="e.g. FDE / AI engineer in fintech, 2.5 years. Built 2 products from scratch. Onboarded customers like … Sign off: cheers, Your Name" /></label>
        <button className="secondary" disabled={!!busy}>Save About you</button></form></details>}
    {data?.found && <form className="brief-form" onSubmit={e => { e.preventDefault(); void work("Researching their site & writing talking points…", async () => { setData(await api<ContactLookup>("/contacts/brief", "POST", { url, company_url: companyUrl.trim() || null })); setNotice("Brief ready. Write the note in your own words, then log what you sent."); }); }}>
      <label>Company website <span className="pill premium">Premium · research</span><input type="url" aria-label="Company website" maxLength={2000} value={companyUrl} onChange={e => setCompanyUrl(e.target.value)} placeholder="https://company.com (optional)" /></label>
      <button className="primary" disabled={!!busy}>{saved ? "Regenerate message brief" : "Generate message brief"}</button>
      <p className="hint">Reads only the company’s own public site (homepage + /about), never LinkedIn. Company facts must quote the site or they’re dropped. Nothing is sent or logged.</p></form>}
    {notice && <p className="hint" role="status">{notice}</p>}
    {saved && <div className="brief-output">{sections.filter(([, items]) => items.length).map(([title, items]) => <div key={title}><h4>{title}</h4><ul>{items.map(i => <li key={i}>{i}</li>)}</ul></div>)}
      {!!saved.research.pages.length && <p className="hint">Sources: {saved.research.pages.map(p => <a key={p} href={p} target="_blank" rel="noreferrer">{p} </a>)}</p>}
      {!!saved.research.dropped_facts && <p className="hint">{saved.research.dropped_facts} company claim(s) dropped: not found on the site.</p>}
      {saved.brief.reference_draft && <details><summary>Reference draft · rewrite it in your own words</summary><blockquote>{saved.brief.reference_draft}</blockquote></details>}
      <button className="secondary" onClick={() => void navigator.clipboard.writeText(copyText).then(() => setNotice("Talking points copied."), e => setError((e as Error).message))}>Copy talking points</button></div>}
  </section>;
}
