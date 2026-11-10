"use client";
import { useEffect, useState } from "react";
import { actionLabels, api, duration, type SessionRecap as Recap } from "@/lib/api";

export function SessionRecap({ sessionId }: { sessionId: string }) {
  const [recap, setRecap] = useState<Recap | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    api<Recap>(`/sessions/${sessionId}/recap`).then(data => { if (active) { setRecap(data); setError(""); } })
      .catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [sessionId, retry]);
  async function reflect() {
    setBusy(true); setError("");
    try { setRecap(await api<Recap>(`/sessions/${sessionId}/recap/analyze`, "POST")); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  function download() {
    const url = URL.createObjectURL(new Blob([JSON.stringify(recap, null, 2)], { type: "application/json" }));
    const link = document.createElement("a"); link.href = url; link.download = `outreach-session-${sessionId}.json`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const p = recap?.payload;
  return <section className="recap" aria-label="Session recap">
    <div className="recap-top"><p className="eyebrow">YOUR SESSION, IN PERSPECTIVE</p><span className="pill">Private recap · v1</span></div>
    <h2>You showed up. Here’s the record.</h2>
    {error && <div className="error" role="alert">{error}<button className="text-button" onClick={() => setRetry(r => r + 1)}>Reload recap</button></div>}
    {!p ? <p className="muted">{error ? "Your activity is saved; the recap is unavailable." : "Preparing your session recap…"}</p> : <>
      <p className="recap-intention">{p.intention}</p>
      <div className="recap-stats"><div><strong>{duration(p.session_seconds)}</strong><span>session time</span></div><div><strong>{p.approved_records}</strong><span>approved records</span></div><div><strong>{p.known_people}</strong><span>known people logged</span></div><div><strong>{p.known_companies}</strong><span>known companies logged</span></div></div>
      <div className="action-breakdown">{Object.entries(actionLabels).map(([key, label]) => { const count = p.action_counts[key as keyof typeof actionLabels] ?? 0; return <div key={key}><span>{label}</span><strong>{count}</strong><div className="count-track"><i style={{ width: `${p.approved_records ? count / p.approved_records * 100 : 0}%` }} /></div></div>; })}</div>
      <ul className="recap-highlights">{p.highlights.map(line => <li key={line}>{line}</li>)}</ul>
      {p.activities.some(a => a.followup_on) && <div className="recap-next"><h3>Your next steps</h3>{p.activities.filter(a => a.followup_on).map(a => <p key={a.capture_id}><strong>{a.followup_on}</strong> · Follow up with {a.person || a.company || "this contact"} <a href={a.source_url} target="_blank" rel="noreferrer">Source ↗</a></p>)}<p className="hint">Dates as recorded at completion. Today’s reminders show current cleared/due status.</p></div>}
      <div className="recap-reflection"><h3>Source-linked observations</h3><p className="hint">Optional AI pass over excerpts of approved notes/source text only. No extra sends, replies, predictions or scores are inferred.</p><button className="secondary" disabled={busy || recap?.reflection?.method === "llm"} onClick={reflect}>{busy ? "Finding supported observations…" : recap?.reflection?.method === "llm" ? "AI observations saved" : "Find AI observations"}</button>
        {recap?.reflection?.warning && <p className="notice">{recap.reflection.warning} Your computed recap is still available.</p>}
        {recap?.reflection?.method === "llm" && <><p className="hint">{recap.reflection.model} · excerpts from {recap.reflection.reviewed_capture_ids.length} approved records</p>{recap.reflection.observations.length === 0 && <p className="muted">No additional source-backed observations found.</p>}{recap.reflection.observations.map((o, i) => <blockquote key={i}>{o.text}<small>Source: {p.activities.find(a => a.capture_id === o.capture_id)?.person || "approved record"}</small><details><summary>Supporting quote</summary>{o.source_quote}</details></blockquote>)}</>}
      </div>
      <div className="button-row"><button className="secondary" onClick={download}>Download session JSON</button><span className="hint">Schema v{p.schema_version} · saved {new Date(p.generated_at).toLocaleString()}</span></div>
      <details><summary>View structured session JSON</summary><pre className="recap-json">{JSON.stringify(recap, null, 2)}</pre></details>
      <p className="hint">{p.discarded_records} discarded · {p.unknown_person_records} records without a known person. Session time is not verified focus; actions are user-confirmed, not platform-verified.</p>
    </>}
  </section>;
}
