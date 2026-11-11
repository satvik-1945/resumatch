"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { api, ApiError, actionLabels, confirmedActions, duration, isProfileUrl, rawText, type Overview, type Session, type User, type Workflow } from "@/lib/api";
import { Auth } from "@/components/auth";
import { CaptureForm } from "@/components/capture-form";
import { PairBrowser } from "@/components/pair-browser";
import { SessionRecap } from "@/components/session-recap";
import { WorkflowHub } from "@/components/workflow-hub";
import { RunAI } from "@/components/run-ai";
import { FilterChips, type ReviewFilter } from "@/components/filter-chips";
import { ContactBrief } from "@/components/contact-brief";

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const expired = useCallback(() => setUser(null), []);
  useEffect(() => { api<User>("/auth/me").then(setUser).catch(e => { if (!(e instanceof ApiError && e.status === 401)) setError(e.message); }).finally(() => setLoading(false)); }, []);
  return <><header className="topbar"><Link className="brand" href="/">resumatch<span> / sessions</span></Link><div className="account"><span className="private-badge">● Private workspace</span>{user && <button className="text-button" onClick={async () => { try { await api("/auth/logout", "POST"); setUser(null); } catch (e) { setError((e as Error).message); } }}>Sign out</button>}</div></header>
    {error && <div className="error global-error" role="alert">{error} <button onClick={() => location.reload()}>Reload</button></div>}
    {loading ? <main className="loading" role="status">Opening your workspace…</main> : user ? <Workspace user={user} expired={expired} /> : <main><Auth onLogin={setUser} /></main>}
  </>;
}
function Workspace({ user, expired }: { user: User; expired: () => void }) {
  const [view, setView] = useState<"today" | "history" | "browser" | "workflows">("today");
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [workflowChoice, setWorkflowChoice] = useState("");
  const [data, setData] = useState<Overview | null>(null);
  const [selected, setSelected] = useState<Session | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [offset, setOffset] = useState(0);
  const [showManual, setShowManual] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [dirtyForms, setDirtyForms] = useState<Set<string>>(() => new Set());
  const [aiBusy, setAiBusy] = useState(false);
  const [bulkIds, setBulkIds] = useState<string[] | null>(null);
  const [bulkResult, setBulkResult] = useState("");
  const [captureFilter, setCaptureFilter] = useState<ReviewFilter>("all");
  const trackDirty = useCallback((id: string, dirty: boolean) => {
    setDirtyForms(previous => {
      if (previous.has(id) === dirty) return previous;
      const next = new Set(previous); if (dirty) next.add(id); else next.delete(id); return next;
    });
  }, []);
  const [clockAt, setClockAt] = useState(0);
  const [tick, setTick] = useState(0);
  const load = useCallback(async () => {
    const [next, parents] = await Promise.all([api<Overview>(`/overview?offset=${offset}`), api<Workflow[]>("/workflows")]);
    setWorkflows(parents);
    setData(next); setClockAt(Date.now());
    setSelected(previous => previous && next.current?.id === previous.id ? next.current : previous);
  }, [offset]);
  const fail = useCallback((e: unknown) => {
    if (e instanceof ApiError && e.status === 401) expired(); else setError((e as Error).message);
  }, [expired]);
  useEffect(() => { const initial = setTimeout(() => void load().catch(fail), 0); const poll = setInterval(() => void load().catch(fail), 5000); return () => { clearTimeout(initial); clearInterval(poll); }; }, [load, fail]);
  useEffect(() => { const timer = setInterval(() => setTick(Date.now()), 1000); return () => clearInterval(timer); }, []);
  async function run(work: () => Promise<unknown>) {
    setBusy(true); setError(""); try { await work(); await load(); } catch (e) { fail(e); } finally { setBusy(false); }
  }
  async function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const f = new FormData(event.currentTarget);
    await run(async () => { const s = await api<Session>("/sessions", "POST", { intention: f.get("intention"), target_minutes: Number(f.get("target_minutes")), workflow_id: f.get("workflow_id"), run_name: f.get("run_name") || undefined }); setSelected(s); setShowManual(false); });
  }
  async function move(action: string) {
    if (!data?.current) return;
    await run(async () => { const s = await api<Session>(`/sessions/${data.current!.id}/transition`, "POST", { action }); setSelected(s); });
  }
  const current = data?.current;
  const defaultRunName = (workflows.find(w => w.id === workflowChoice) ?? workflows[0])?.next_run_name;
  const session = view === "today" ? current ?? (selected?.state === "completed" ? selected : null) : selected;
  const captures = session?.captures ?? [];
  const pending = captures.filter(c => c.decision === "pending");
  const discardedCount = captures.filter(c => c.decision === "discarded").length;
  const captureCounts = { all: captures.length, pending: pending.length, approved: captures.filter(c => c.decision === "approved").length, ...(discardedCount ? { discarded: discardedCount } : {}) };
  const shownCaptures = captures.filter(c => captureFilter === "all" || c.decision === captureFilter);
  // Bulk approval never covers actions you must personally confirm or possible duplicates.
  const bulkEligible = pending.filter(c => !confirmedActions.includes(c.details.action) && !c.duplicate_of && !c.same_raw_text_as);
  async function bulkApprove(ids: string[]) {
    if (!session) return;
    setBulkIds(null);
    await run(async () => {
      const result = await api<{ approved: string[]; skipped: { id: string; reason: string }[]; session: Session }>(`/sessions/${session.id}/captures/bulk-approve`, "POST", { capture_ids: ids });
      setSelected(result.session);
      setBulkResult(`Approved ${result.approved.length} record${result.approved.length === 1 ? "" : "s"}.${result.skipped.length ? ` ${result.skipped.length} left pending for individual review.` : ""}`);
    });
  }
  const shownElapsed = session ? session.elapsed_seconds + (session.state === "active" ? Math.max(0, Math.floor((tick - clockAt) / 1000)) : 0) : 0;
  return <div className="shell"><aside className="sidebar"><p className="eyebrow">MAKE YOUR NEXT MOVE</p><nav aria-label="Workspace"><button className={view === "today" ? "active" : ""} onClick={() => setView("today")}>◉ <span>Today</span></button><button className={view === "workflows" ? "active" : ""} onClick={() => setView("workflows")}>▤ <span>Workflows</span></button><button className={view === "history" ? "active" : ""} onClick={() => { setView("history"); setSelected(null); }}>↗ <span>Run history</span></button><button className={view === "browser" ? "active" : ""} onClick={() => setView("browser")}>▣ <span>Browser capture</span></button></nav><div className="sidebar-note"><strong>Same purpose. A new day.</strong><p>Workflows hold your fields.<br />Runs hold your daily effort.<br />Review makes it count.</p></div><span className="account-name">{user.email}</span></aside>
    <main className="workspace"><div className="breadcrumb">Your workspace / {view === "today" ? "Today" : view === "history" ? "Run history" : view === "workflows" ? "Workflows" : "Browser capture"}</div>
      {error && <div role="alert" className="error">{error}<button className="text-button" onClick={() => { setError(""); void load().catch(fail); }}>Retry</button></div>}
      {!data ? <div className="panel" role="status">Loading your runs…</div> : view === "browser" ? <PairBrowser /> : view === "workflows" ? <WorkflowHub workflows={workflows} refresh={load} onRun={w => { setWorkflowChoice(w.id); setView("today"); }} onOpen={id => run(async () => { const s = await api<Session>(`/sessions/${id}`); setSelected(s); setView(s.state === "completed" ? "history" : "today"); })} /> : <>
        <header className="section-title"><p className="eyebrow">{view === "today" ? "A LITTLE OUTREACH. REAL PROGRESS." : "THE WORK BEHIND THE OPPORTUNITY"}</p><h1>{view === "today" ? "Make one good connection." : "Look how far you’ve come."}</h1><p className="lede">{view === "today" ? "Start small. Explore a company, reach out to someone, or follow up. Keep an honest record of the effort." : "Your private, reviewed session history. The small steps add up."}</p></header>
        {view === "today" && <div className="stats"><section><p>THIS WEEK · UTC</p><strong>{data.week.sessions}<small> / {data.week.target} runs</small></strong><progress value={data.week.sessions} max={Math.max(data.week.target, data.week.sessions)} /><label className="goal-label">Weekly target<select aria-label="Weekly session target" value={data.week.target} disabled={busy} onChange={e => run(() => api("/goal", "PUT", { weekly_target: Number(e.target.value) }))}>{Array.from({ length: 14 }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}</select></label><p className="hint">Completed runs with at least one approved record.</p></section><section><p>REVIEWED THIS WEEK</p><div className="mini-counts"><span><strong>{data.week.counts.connection_requested ?? 0}</strong>Requests sent</span><span><strong>{data.week.counts.sent ?? 0}</strong>Initial messages</span><span><strong>{data.week.counts.followed_up ?? 0}</strong>Follow-ups</span><span><strong>{data.week.counts.replied ?? 0}</strong>Replies</span></div><p className="hint">User-confirmed actions, grouped by approval date. Research and drafts aren’t sends.</p></section></div>}
        {view === "today" && !current && <section className="start-card"><div><span className="pill">YOUR NEXT RUN</span><h2>Same workflow.<br />Another good session.</h2><p>Run this workflow as many times as you need today. Each session has its own name and records.</p><button className="text-button" onClick={() => setView("workflows")}>Create or manage workflows</button></div>{workflows.length ? <form onSubmit={start}><label>Workflow<select name="workflow_id" required value={workflowChoice || workflows[0].id} onChange={e => setWorkflowChoice(e.target.value)}>{workflows.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}</select></label><label>Run name<input name="run_name" aria-label="Run name" maxLength={200} placeholder={defaultRunName || "Optional session name"} /><span className="hint">Optional. Leave blank for {defaultRunName || "the next date-based name"}. Repeat runs use (1), (2), … within this workflow. Dates use UTC.</span></label><label>Session intention<input name="intention" required maxLength={200} placeholder="What are you doing in this run?" /></label><label>Time intention<select name="target_minutes" defaultValue="25"><option value="15">15 minutes</option><option value="25">25 minutes</option><option value="45">45 minutes</option><option value="60">60 minutes</option></select></label><button className="primary" disabled={busy}>Start run ↗</button></form> : <div><h3>Create your first workflow</h3><p>Start with fintech founder connections or contact outreach, then customize its fields.</p><button className="primary" onClick={() => setView("workflows")}>Create a workflow</button></div>}</section>}
        {session && <section className="panel session-panel"><div className="session-heading"><div><span className={`pill ${session.state}`}>{session.state === "review" ? "Ready for review" : session.state}</span><h2>{session.intention}</h2><p className="hint">{new Date(session.started_at).toLocaleString()} · {session.target_minutes}-minute intention</p></div><div className="timer"><strong>{duration(shownElapsed)}</strong><span>Session time · not verified focus</span></div></div>
          <div className="run-context"><div><p className="eyebrow">{session.workflow_name} · RUN FIELDS V{session.workflow_version}</p><form key={session.id} className="rename-run" onSubmit={e => { e.preventDefault(); const name = new FormData(e.currentTarget).get("run_name"); void run(async () => setSelected(await api(`/sessions/${session.id}/name`, "PUT", { run_name: name }))); }}><label>Run name<input name="run_name" required maxLength={200} defaultValue={session.run_name} /></label><button className="secondary" disabled={busy}>Rename run</button></form></div>{workflows.find(w => w.id === session.workflow_id)?.version !== session.workflow_version && session.state !== "completed" && <button className="secondary" disabled={busy} onClick={() => run(async () => setSelected(await api(`/sessions/${session.id}/sync-workflow`, "POST")))}>Use latest workflow fields</button>}</div>
          <RunAI key={session.id} session={session} hasUnsavedEdits={dirtyForms.size > 0} onBusyChange={setAiBusy} refresh={async () => { await load(); setSelected(await api(`/sessions/${session.id}`)); }} />
          {session.state === "active" || session.state === "paused" ? <><div className="button-row"><button className="secondary" disabled={busy} onClick={() => move(session.state === "active" ? "pause" : "resume")}>{session.state === "active" ? "Pause session" : "Resume session"}</button><button className="primary" disabled={busy || aiBusy || dirtyForms.size > 0} onClick={() => move("finish")}>Finish & review</button></div><div className="capture-prompt"><div><h3>{session.state === "paused" ? "Take your time." : "Browse. Connect. Capture."}</h3><p>{session.state === "paused" ? "Your timer is stopped. Resume when you’re ready to capture again." : "Use the browser extension on a page you want to save, or add a quick record here."}</p></div><button className="secondary" onClick={() => setView("browser")}>Set up browser capture</button></div>{session.state === "active" && <><button className="text-button" onClick={() => setShowManual(!showManual)}>{showManual ? "Close manual capture" : "+ Add a quick manual capture"}</button>{showManual && <CaptureForm sessionId={session.id} fields={session.field_definition} locked={aiBusy} onDirtyChange={trackDirty} onSaved={load} />}</>}</> : null}
          <div className="panel-heading"><h3>{session.state === "review" ? "Check what happened" : session.state === "completed" ? "Your reviewed activity" : "Captured so far"}</h3><span className="muted">{session.pending_count} pending · {session.approved_count} approved</span></div>
          {session.state === "review" && pending.length > 0 && <div className="bulk-approve">{bulkIds ? <><p>Approve {bulkIds.length} record{bulkIds.length === 1 ? "" : "s"} exactly as saved? {pending.length - bulkIds.length} stay pending for individual review.</p><div className="button-row"><button className="primary" disabled={busy || aiBusy || dirtyForms.size > 0} onClick={() => bulkApprove(bulkIds)}>Yes, approve {bulkIds.length}</button><button className="secondary" onClick={() => setBulkIds(null)}>Cancel</button></div></> : <><button className="secondary" disabled={busy || aiBusy || dirtyForms.size > 0 || !bulkEligible.length} onClick={() => { setBulkResult(""); setBulkIds(bulkEligible.map(c => c.id)); }}>Approve all eligible ({bulkEligible.length})</button><p className="hint">{dirtyForms.size > 0 ? "Save or cancel unsaved edits first. " : ""}Skips sent requests, messages, follow-ups and replies (confirm those yourself) and possible duplicates.</p></>}{bulkResult && <p role="status" className="hint">{bulkResult}</p>}</div>}
          {captures.length > 0 && <FilterChips value={captureFilter} counts={captureCounts} onChange={setCaptureFilter} noun="records" />}
          {captures.length > 0 && !shownCaptures.length && <p className="muted">No records match this filter.</p>}
          {!session.captures?.length && <div className="empty"><span>◎</span><h3>Room for your first small step.</h3><p>No captures yet. Research, drafts and conversations each have their own place here.</p></div>}
          {shownCaptures.map(c => <article className="capture" key={c.id}><div className="capture-heading"><strong>{c.details.person || c.details.company || c.details.source_title || "Research capture"}</strong><span className={`pill ${c.decision}`}>{c.decision}</span></div><p className="hint">{actionLabels[c.details.action]} · {c.details.channel} · {c.source === "browser" ? "Browser captured" : "Manually entered"}</p>
            <div className="capture-facts"><span><strong>Company</strong>{c.details.company || "Not recorded"}</span><span><strong>Activity</strong>{c.details.occurred_at ? new Date(c.details.occurred_at).toLocaleString() : "Not recorded"}</span><span><strong>Follow-up</strong>{c.details.followup_on ? `${c.details.followup_on}${c.followup_done ? " · cleared" : c.decision === "pending" ? " · planned, awaiting approval" : c.decision === "discarded" ? " · not scheduled" : " · reminder set"}` : "No reminder set"}</span></div>
            {c.same_raw_text_as && <p className="notice">Same pasted text as another record with a different profile URL, probably a stale clipboard. Check which profile this text belongs to, then re-paste the right text or discard the extra.</p>}
            {c.duplicate_of && <p className="notice">Possible duplicate already in this session. Keep one record; edit its details and discard the extra during review.</p>}
            {c.analysis?.schema_version === 2 && <p className="hint">{c.analysis.method === "llm" ? "AI processed" : "Local fallback"} · {c.analysis.filled_fields.length} fields filled · {c.analysis.preserved_fields.length} existing values preserved{c.analysis.warning ? ` · ${c.analysis.warning}` : ""}</p>}
            {session.workflow_kind === "contact_outreach" && c.decision !== "discarded" && isProfileUrl(c.details.source_url) && <ContactBrief url={c.details.source_url} />}
            {(session.state === "active" || session.state === "paused") && c.decision === "pending" && <><button className="text-button" onClick={() => setEditingId(editingId === c.id ? null : c.id)}>{editingId === c.id ? "Cancel editing" : "Edit capture"}</button>{editingId === c.id && <CaptureForm sessionId={session.id} capture={c} fields={session.field_definition} editing locked={aiBusy} onDirtyChange={trackDirty} onSaved={async () => { await load(); setEditingId(null); }} />}</>}
            {session.state === "review" && c.decision === "pending" ? <CaptureForm key={`${c.id}-${session.workflow_version}`} sessionId={session.id} capture={c} fields={session.field_definition} compact={(session.captures?.length || 0) > 1} locked={aiBusy} onDirtyChange={trackDirty} onSaved={async () => { await load(); setSelected(await api(`/sessions/${session.id}`)); }} /> : <><a href={c.details.source_url} target="_blank" rel="noreferrer">{c.details.source_title || c.details.source_url} ↗</a>{rawText(c.details) && <details><summary>Raw capture text</summary><blockquote>{rawText(c.details)}</blockquote></details>}<div className="field-chips">{session.field_definition.filter(f => !["contact_url", "person", "company"].includes(f.key) && c.details.fields?.[f.key] != null).map(f => <span key={f.key}><strong>{f.label}:</strong> {String(c.details.fields?.[f.key])}</span>)}</div>{c.decision === "approved" && <span className="hint">Reviewed by you · {c.details.person || "Person unknown"}{c.details.company ? ` · ${c.details.company}` : ""}</span>}</>}
          </article>)}
          {session.state === "review" && <div className="review-footer"><p>Only approved records contribute to progress. Discard anything that doesn’t belong.</p><button className="primary" disabled={busy || session.pending_count > 0} onClick={() => move("complete")}>Complete session</button></div>}
          {session.state === "completed" && <><div className="success" role="status">Session saved. {session.approved_count} approved record{session.approved_count === 1 ? "" : "s"}. One more step forward.</div><SessionRecap key={session.id} sessionId={session.id} /></>}
        </section>}
        {view === "history" && <section className="panel"><div className="panel-heading"><h2>Your runs</h2><span className="hint">Newest first</span></div>{!data.history.length && <div className="empty"><h3>Your story starts with one run.</h3><button className="secondary" onClick={() => setView("today")}>Start today</button></div>}{data.history.map(s => <button className="history-row" key={s.id} onClick={() => run(async () => { setSelected(await api(`/sessions/${s.id}`)); if (s.state !== "completed") setView("today"); })}><span><strong>{s.run_name}</strong><small>{s.workflow_name} · {s.intention} · {s.state}</small></span><span>{duration(s.elapsed_seconds)}<small>{s.approved_count} approved · {s.pending_count} pending</small></span><span aria-hidden="true">↗</span></button>)}<div className="button-row"><button className="secondary" disabled={offset === 0 || busy} onClick={() => setOffset(Math.max(0, offset - 20))}>Newer</button><button className="secondary" disabled={data.history.length < 20 || busy} onClick={() => setOffset(offset + 20)}>Older</button></div></section>}
        {view === "today" && <div className="bottom-grid"><section className="panel"><p className="eyebrow">KEEP THE CONVERSATION GOING</p><h2>Due follow-ups <span className="muted">{data.followups.length}</span></h2>{!data.followups.length ? <p className="muted">Nothing due. Add a reminder to a capture and approve it to bring it here.</p> : data.followups.map(c => <div className="list-row" key={c.id}><div><strong>{c.details.person || c.details.company || "Follow-up"}</strong><p className="hint">{c.details.followup_on} · {c.details.channel}</p><a href={c.details.source_url} target="_blank" rel="noreferrer">Open source ↗</a></div><button className="secondary" disabled={busy} onClick={() => run(() => api(`/captures/${c.id}/followup-done`, "POST"))}>Clear reminder</button></div>)}<p className="hint">Clearing a reminder doesn’t log a sent follow-up. Capture the actual action in a session.</p></section><section className="panel discovery"><p className="eyebrow">A SOURCE TO EXPLORE</p><h2>Find something worth a conversation.</h2><p>daily.dev has an official MCP server and developer-news feeds. Open a story, select useful context, and capture it as research.</p><a className="secondary link-button" href="https://daily.dev/" target="_blank" rel="noreferrer">Explore daily.dev ↗</a><a className="text-button" href="https://docs.daily.dev/mcp-server/" target="_blank" rel="noreferrer">Official MCP setup</a><p className="hint">Manual source link, not a connected feed. Funding and contact details still need verification.</p></section></div>}
        {view === "today" && <section className="panel"><p className="eyebrow">ON YOUR HORIZON</p><h2>Upcoming follow-ups <span className="muted">{data.upcoming_followups.length}</span></h2>{data.upcoming_followups.length ? data.upcoming_followups.map(c => <div className="list-row" key={c.id}><div><strong>{c.details.person || c.details.company || "Follow-up"}</strong><p className="hint">{c.details.followup_on} · {c.details.channel}</p></div><a href={c.details.source_url} target="_blank" rel="noreferrer">Open source ↗</a></div>) : <p className="muted">No future reminders yet. Choose a follow-up date while capturing or reviewing; it appears here after approval.</p>}</section>}
      </>}
      <footer>Your pace. Your progress. Always private.</footer>
    </main></div>;
}
