"use client";
import { useEffect, useState } from "react";
import { actionLabels, api, duration, type SessionRecap as Recap } from "@/lib/api";
import { workflowStyle } from "@/lib/palette";
import { AppIcon } from "./app-icon";

export function SessionRecap({ sessionId, celebrate = false, compact = false, onReplay }: {
  sessionId: string; celebrate?: boolean; compact?: boolean; onReplay?: () => void;
}) {
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
  const progress = recap?.progress;
  const hasActivity = !!p?.approved_records;
  return <section className={`recap ${celebrate && hasActivity ? "celebrate" : ""} ${compact ? "recap-compact" : ""}`} aria-label="Session recap" style={workflowStyle(progress?.color)}>
    {error && <div className="error" role="alert">{error}<button className="text-button" onClick={() => setRetry(r => r + 1)}>Reload recap</button></div>}
    {!p ? <div className="recap-loading" role="status"><span className="loading-ring" />Preparing your session summary…</div> : <>
      <header className="recap-hero"><div className="finish-mark" aria-hidden="true"><svg viewBox="0 0 80 80"><circle className="finish-track" cx="40" cy="40" r="34" /><circle className="finish-ring" cx="40" cy="40" r="34" /></svg><AppIcon name="check" size={32} /><i /><i /><i /><i /></div><p className="eyebrow">{progress?.workflow_name || "YOUR OUTREACH SESSION"}</p><h2>{hasActivity ? "Session complete." : "Session saved."}</h2><p>{hasActivity ? "You made time for your next move." : "No approved activity this time. Your session is still saved."}</p><span className="recap-run">{progress?.run_name || p.intention} · {new Date(p.completed_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</span></header>
      <div className="recap-stats"><div><strong>{duration(p.session_seconds)}</strong><span>session time</span></div><div><strong>{p.approved_records}</strong><span>approved records</span></div><div><strong>{p.known_people}</strong><span>people recorded</span></div><div><strong>{p.known_companies}</strong><span>companies recorded</span></div></div>
      {hasActivity && <div className="recap-comparison" aria-label="Previous run comparison">
        {progress?.personal_best_records && <span className="best-mark">Personal best · approved records</span>}
        {progress?.previous ? <><strong>{progress.record_delta === 0 ? "Same number of approved records" : `${Math.abs(progress.record_delta ?? 0)} ${progress.record_delta! > 0 ? "more" : "fewer"} approved records`}</strong><p>Compared with {progress.previous.run_name} in this workflow ({progress.previous.approved_records} approved).</p><span>{progress.time_delta_seconds === 0 ? "Same session duration." : `${duration(Math.abs(progress.time_delta_seconds ?? 0))} ${progress.time_delta_seconds! > 0 ? "more" : "less"} session time.`} Volume and time aren’t a measure of relationship quality.</span></> : <><strong>Your first reviewed run in this workflow.</strong><p>This is your baseline. The next session adds to the story.</p></>}
      </div>}
      <div className="action-breakdown">{Object.entries(actionLabels).map(([key, label]) => { const count = p.action_counts[key as keyof typeof actionLabels] ?? 0; return <div key={key}><span>{label}</span><strong>{count}</strong><div className="count-track"><i style={{ width: `${p.approved_records ? count / p.approved_records * 100 : 0}%` }} /></div></div>; })}</div>
      {!compact && <>
        <ul className="recap-highlights">{p.highlights.map(line => <li key={line}>{line}</li>)}</ul>
        {p.activities.some(a => a.followup_on) && <div className="recap-next"><h3>Keep the conversation going</h3>{p.activities.filter(a => a.followup_on).map(a => <p key={a.capture_id}><strong>{a.followup_on}</strong> · {a.person || a.company || "Follow-up"} <a href={a.source_url} target="_blank" rel="noreferrer">Source ↗</a></p>)}<p className="hint">Dates recorded at completion. Today’s reminders show current cleared/due status.</p></div>}
        <details className="recap-reflection"><summary>Source-linked AI observations</summary><p className="hint">Optional excerpts from approved notes. They never change these metrics.</p><button className="secondary" disabled={busy || recap?.reflection?.method === "llm"} onClick={reflect}>{busy ? "Finding supported observations…" : recap?.reflection?.method === "llm" ? "AI observations saved" : "Find AI observations"}</button>
          {recap?.reflection?.warning && <p className="notice">{recap.reflection.warning} Your computed recap is still available.</p>}
          {recap?.reflection?.method === "llm" && <><p className="hint">{recap.reflection.model} · excerpts from {recap.reflection.reviewed_capture_ids.length} approved records</p>{recap.reflection.observations.length === 0 && <p className="muted">No additional source-backed observations found.</p>}{recap.reflection.observations.map((o, i) => <blockquote key={i}>{o.text}<small>Source: {p.activities.find(a => a.capture_id === o.capture_id)?.person || "approved record"}</small><details><summary>Supporting quote</summary>{o.source_quote}</details></blockquote>)}</>}
        </details>
        <div className="button-row"><button className="secondary" onClick={download}>Download session JSON</button>{onReplay && <button className="text-button" onClick={onReplay}>Replay completion</button>}<span className="hint">Private · schema v{p.schema_version}</span></div>
        <details><summary>View structured session JSON</summary><pre className="recap-json">{JSON.stringify(recap, null, 2)}</pre></details>
      </>}
      <p className="recap-footnote">{p.discarded_records} discarded · {p.unknown_person_records} without a known person. Session time is not verified focus. Actions are user-confirmed.</p>
    </>}
  </section>;
}
