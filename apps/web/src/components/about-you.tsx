"use client";
import { useEffect, useState } from "react";
import { AiFeedback } from "@/components/ai-feedback";
import { api, type PersonaPoint, type Profile } from "@/lib/api";

const MAX_FILE_BYTES = 4_000_000;

function fileBase64(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] ?? "");
    reader.onerror = () => reject(new Error("Could not read that file."));
    reader.readAsDataURL(file);
  });
}

function Points({ title, items }: { title: string; items: PersonaPoint[] }) {
  if (!items.length) return null;
  return <div><h4>{title}</h4><ul>{items.map(p => <li key={p.point}>{p.point}<small>“{p.evidence}”</small></li>)}</ul></div>;
}

// The sender's own background. Message briefs pick credentials only from this page.
export function AboutYou() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [resume, setResume] = useState("");
  const [about, setAbout] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => {
    api<Profile>("/profile").then(p => { setProfile(p); setResume(p.resume_text); setAbout(p.about_me); }, e => setError((e as Error).message));
  }, []);
  const dirty = !!profile && (resume.trim() !== profile.resume_text || about.trim() !== profile.about_me);
  async function work(label: string, task: () => Promise<void>) {
    setBusy(label); setError(""); setNotice("");
    try { await task(); } catch (e) { setError((e as Error).message); } finally { setBusy(""); }
  }
  async function save() {
    const saved = await api<Profile>("/profile", "PUT", { about_me: about, resume_text: resume });
    setProfile(saved); setResume(saved.resume_text); setAbout(saved.about_me);
  }
  const upload = (file: File | undefined) => file && work("Reading your resume…", async () => {
    if (file.size > MAX_FILE_BYTES) throw new Error("Resume file is larger than 4 MB.");
    const { resume_text } = await api<{ resume_text: string }>("/profile/resume-file", "POST", { filename: file.name, content_base64: await fileBase64(file) });
    setResume(resume_text); setNotice("Resume text extracted. Check it, then save.");
  });
  const persona = profile?.persona;
  if (!profile) return <section className="panel" role="status">{error ? <p className="error" role="alert">{error}</p> : "Loading your profile…"}</section>;
  return <>
    <header className="section-title"><p className="eyebrow">YOUR SIDE OF THE CONVERSATION</p><h1>About you</h1><p className="lede">Add your resume once. Your persona is built from it, and message briefs pick one matching credential from it for each person you reach out to.</p></header>
    {persona && <section className="panel persona" aria-label="Your persona">
      <div className="panel-heading"><div><p className="eyebrow">YOUR PERSONA</p><h2>{persona.headline || "Your persona"}</h2></div>{persona.stale && <span className="pill pending">Resume changed · rebuild</span>}</div>
      {persona.summary && <p>{persona.summary}</p>}
      {!!persona.domains.length && <div className="field-chips">{persona.domains.map(d => <span key={d}>{d}</span>)}</div>}
      <div className="persona-grid"><Points title="Proof points" items={persona.proof_points} /><Points title="Strengths" items={persona.strengths} /></div>
      <p className="hint">Every point quotes your resume.{persona.dropped ? ` ${persona.dropped} unquoted point(s) dropped.` : ""} Built {new Date(persona.generated_at).toLocaleString()}.</p>
      {persona.ai_run_id && <AiFeedback key={persona.ai_run_id} runId={persona.ai_run_id} />}
    </section>}
    <section className="panel">
      <form onSubmit={e => { e.preventDefault(); void work("Saving…", async () => { await save(); setNotice("Saved."); }); }}>
        <label>Your resume<span className="optional">Paste the text, or upload a PDF / .txt / .md. Nothing is shared.</span>
          <textarea aria-label="Your resume" rows={14} maxLength={30000} value={resume} onChange={e => setResume(e.target.value)} placeholder="Paste your resume text here…" /></label>
        <label className="file-pick">Upload resume file<input type="file" aria-label="Upload resume file" accept=".pdf,.txt,.md,application/pdf,text/plain" disabled={!!busy} onChange={e => { void upload(e.target.files?.[0]); e.target.value = ""; }} /></label>
        <label>About you · in your own words<span className="optional">What you’re looking for, how you sound, how you sign off. e.g. “Looking for founding-engineer roles in fintech. Casual tone. Sign off: cheers, Satvik”</span>
          <textarea aria-label="About you" rows={4} maxLength={3000} value={about} onChange={e => setAbout(e.target.value)} /></label>
        <div className="button-row"><button className="secondary" disabled={!!busy || !dirty}>Save</button>
          <button type="button" className="primary" disabled={!!busy || !resume.trim()} onClick={() => void work("Building your persona from your resume…", async () => { if (dirty) await save(); setProfile(await api<Profile>("/profile/persona", "POST")); setNotice("Persona ready."); })}>{persona ? "Rebuild persona" : "Build my persona"}</button></div>
        {dirty && <p className="hint">Unsaved changes. Building the persona saves them first.</p>}
      </form>
      {busy && <p className="hint" role="status">{busy}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="hint" role="status">{notice}</p>}
    </section>
  </>;
}
