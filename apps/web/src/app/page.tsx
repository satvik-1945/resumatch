"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { api, ApiError, actionLabels, duration, type Overview, type Session, type User } from "@/lib/api";
import { Auth } from "@/components/auth";
import { CaptureForm } from "@/components/capture-form";
import { PairBrowser } from "@/components/pair-browser";
import { SessionRecap } from "@/components/session-recap";

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
  const [view, setView] = useState<"today" | "history" | "browser">("today");
  const [data, setData] = useState<Overview | null>(null);
  const [selected, setSelected] = useState<Session | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [offset, setOffset] = useState(0);
  const [showManual, setShowManual] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [clockAt, setClockAt] = useState(0);
  const [tick, setTick] = useState(0);
  const load = useCallback(async () => {
    const next = await api<Overview>(`/overview?offset=${offset}`);
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
    await run(async () => { const s = await api<Session>("/sessions", "POST", { intention: f.get("intention"), target_minutes: Number(f.get("target_minutes")) }); setSelected(s); setShowManual(false); });
  }
  async function move(action: string) {
    if (!data?.current) return;
    await run(async () => { const s = await api<Session>(`/sessions/${data.current!.id}/transition`, "POST", { action }); setSelected(s); });
  }
  const current = data?.current;
  const session = view === "today" ? current ?? (selected?.state === "completed" ? selected : null) : selected;
  const shownElapsed = session ? session.elapsed_seconds + (session.state === "active" ? Math.max(0, Math.floor((tick - clockAt) / 1000)) : 0) : 0;
  return <div className="shell"><aside className="sidebar"><p className="eyebrow">MAKE YOUR NEXT MOVE</p><nav aria-label="Workspace"><button className={view === "today" ? "active" : ""} onClick={() => setView("today")}>◉ <span>Today</span></button><button className={view === "history" ? "active" : ""} onClick={() => { setView("history"); setSelected(null); }}>↗ <span>Session history</span></button><button className={view === "browser" ? "active" : ""} onClick={() => setView("browser")}>▣ <span>Browser capture</span></button></nav><div className="sidebar-note"><strong>Progress, at your pace.</strong><p>Research counts as research.<br />Drafts stay drafts.<br />You decide what gets logged.</p></div><span className="account-name">{user.email}</span></aside>
    <main className="workspace"><div className="breadcrumb">Your workspace / {view === "today" ? "Today" : view === "history" ? "History" : "Browser capture"}</div>
      {error && <div role="alert" className="error">{error}<button className="text-button" onClick={() => { setError(""); void load().catch(fail); }}>Retry</button></div>}
      {!data ? <div className="panel" role="status">Loading your sessions…</div> : view === "browser" ? <PairBrowser /> : <>
        <header className="section-title"><p className="eyebrow">{view === "today" ? "A LITTLE OUTREACH. REAL PROGRESS." : "THE WORK BEHIND THE OPPORTUNITY"}</p><h1>{view === "today" ? "Make one good connection." : "Look how far you’ve come."}</h1><p className="lede">{view === "today" ? "Start small. Explore a company, reach out to someone, or follow up. Keep an honest record of the effort." : "Your private, reviewed session history. The small steps add up."}</p></header>
        {view === "today" && <div className="stats"><section><p>THIS WEEK · UTC</p><strong>{data.week.sessions}<small> / {data.week.target} sessions</small></strong><progress value={data.week.sessions} max={Math.max(data.week.target, data.week.sessions)} /><label className="goal-label">Weekly target<select aria-label="Weekly session target" value={data.week.target} disabled={busy} onChange={e => run(() => api("/goal", "PUT", { weekly_target: Number(e.target.value) }))}>{Array.from({ length: 14 }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}</select></label><p className="hint">Completed sessions with at least one approved record.</p></section><section><p>REVIEWED THIS WEEK</p><div className="mini-counts"><span><strong>{data.week.counts.sent ?? 0}</strong>Initial sends</span><span><strong>{data.week.counts.followed_up ?? 0}</strong>Follow-ups</span><span><strong>{data.week.counts.replied ?? 0}</strong>Replies</span></div><p className="hint">User-confirmed actions, grouped by approval date. Research and drafts aren’t sends.</p></section></div>}
        {view === "today" && !current && <section className="start-card"><div><span className="pill">YOUR NEXT SESSION</span><h2>A small intention.<br />A meaningful next step.</h2><p>What would make this session worthwhile?</p></div><form onSubmit={start}><label>Session intention<input name="intention" required maxLength={200} placeholder="Find and contact a fintech founder" /></label><label>Time intention<select name="target_minutes" defaultValue="25"><option value="15">15 minutes · A quick check-in</option><option value="25">25 minutes · One focused session</option><option value="45">45 minutes · Go a little deeper</option><option value="60">60 minutes · Research & outreach</option></select></label><button className="primary" disabled={busy}>Start session <span aria-hidden="true">↗</span></button></form></section>}
        {session && <section className="panel session-panel"><div className="session-heading"><div><span className={`pill ${session.state}`}>{session.state === "review" ? "Ready for review" : session.state}</span><h2>{session.intention}</h2><p className="hint">{new Date(session.started_at).toLocaleString()} · {session.target_minutes}-minute intention</p></div><div className="timer"><strong>{duration(shownElapsed)}</strong><span>Session time · not verified focus</span></div></div>
          {session.state === "active" || session.state === "paused" ? <><div className="button-row"><button className="secondary" disabled={busy} onClick={() => move(session.state === "active" ? "pause" : "resume")}>{session.state === "active" ? "Pause session" : "Resume session"}</button><button className="primary" disabled={busy} onClick={() => move("finish")}>Finish & review</button></div><div className="capture-prompt"><div><h3>{session.state === "paused" ? "Take your time." : "Browse. Connect. Capture."}</h3><p>{session.state === "paused" ? "Your timer is stopped. Resume when you’re ready to capture again." : "Use the browser extension on a page you want to save, or add a quick record here."}</p></div><button className="secondary" onClick={() => setView("browser")}>Set up browser capture</button></div>{session.state === "active" && <><button className="text-button" onClick={() => setShowManual(!showManual)}>{showManual ? "Close manual capture" : "+ Add a quick manual capture"}</button>{showManual && <CaptureForm sessionId={session.id} onSaved={load} />}</>}</> : null}
          <div className="panel-heading"><h3>{session.state === "review" ? "Check what happened" : session.state === "completed" ? "Your reviewed activity" : "Captured so far"}</h3><span className="muted">{session.pending_count} pending · {session.approved_count} approved</span></div>
          {!session.captures?.length && <div className="empty"><span>◎</span><h3>Room for your first small step.</h3><p>No captures yet. Research, drafts and conversations each have their own place here.</p></div>}
          {session.captures?.map(c => <article className="capture" key={c.id}><div className="capture-heading"><strong>{c.details.person || c.details.company || c.details.source_title || "Research capture"}</strong><span className={`pill ${c.decision}`}>{c.decision}</span></div><p className="hint">{actionLabels[c.details.action]} · {c.details.channel} · {c.source === "browser" ? "Browser captured" : "Manually entered"}</p>
            <div className="capture-facts"><span><strong>Company</strong>{c.details.company || "Not recorded"}</span><span><strong>Activity</strong>{c.details.occurred_at ? new Date(c.details.occurred_at).toLocaleString() : "Not recorded"}</span><span><strong>Follow-up</strong>{c.details.followup_on ? `${c.details.followup_on}${c.followup_done ? " · cleared" : c.decision === "pending" ? " · planned, awaiting approval" : c.decision === "discarded" ? " · not scheduled" : " · reminder set"}` : "No reminder set"}</span></div>
            {c.duplicate_of && <p className="notice">Possible duplicate already in this session. Keep one record; edit its details and discard the extra during review.</p>}
            {(session.state === "active" || session.state === "paused") && c.decision === "pending" && <><button className="text-button" onClick={() => setEditingId(editingId === c.id ? null : c.id)}>{editingId === c.id ? "Cancel editing" : "Edit capture"}</button>{editingId === c.id && <CaptureForm sessionId={session.id} capture={c} editing onSaved={async () => { await load(); setEditingId(null); }} />}</>}
            {session.state === "review" && c.decision === "pending" ? <CaptureForm sessionId={session.id} capture={c} onSaved={async () => { await load(); setSelected(await api(`/sessions/${session.id}`)); }} /> : <><a href={c.details.source_url} target="_blank" rel="noreferrer">{c.details.source_title || c.details.source_url} ↗</a>{c.details.notes && <p className="preserve">{c.details.notes}</p>}{c.details.quote && <details><summary>Source text</summary><blockquote>{c.details.quote}</blockquote></details>}{c.decision === "approved" && <span className="hint">Reviewed by you · {c.details.person || "Person unknown"}{c.details.company ? ` · ${c.details.company}` : ""}</span>}</>}
          </article>)}
          {session.state === "review" && <div className="review-footer"><p>Only approved records contribute to progress. Discard anything that doesn’t belong.</p><button className="primary" disabled={busy || session.pending_count > 0} onClick={() => move("complete")}>Complete session</button></div>}
          {session.state === "completed" && <><div className="success" role="status">Session saved. {session.approved_count} approved record{session.approved_count === 1 ? "" : "s"}. One more step forward.</div><SessionRecap key={session.id} sessionId={session.id} /></>}
        </section>}
        {view === "history" && <section className="panel"><div className="panel-heading"><h2>Your sessions</h2><span className="hint">Newest first</span></div>{!data.history.length && <div className="empty"><h3>Your story starts with one session.</h3><button className="secondary" onClick={() => setView("today")}>Start today</button></div>}{data.history.map(s => <button className="history-row" key={s.id} onClick={() => run(async () => { setSelected(await api(`/sessions/${s.id}`)); if (s.state !== "completed") setView("today"); })}><span><strong>{s.intention}</strong><small>{new Date(s.started_at).toLocaleDateString()} · {s.state}</small></span><span>{duration(s.elapsed_seconds)}<small>{s.approved_count} approved · {s.pending_count} pending</small></span><span aria-hidden="true">↗</span></button>)}<div className="button-row"><button className="secondary" disabled={offset === 0 || busy} onClick={() => setOffset(Math.max(0, offset - 20))}>Newer</button><button className="secondary" disabled={data.history.length < 20 || busy} onClick={() => setOffset(offset + 20)}>Older</button></div></section>}
        {view === "today" && <div className="bottom-grid"><section className="panel"><p className="eyebrow">KEEP THE CONVERSATION GOING</p><h2>Due follow-ups <span className="muted">{data.followups.length}</span></h2>{!data.followups.length ? <p className="muted">Nothing due. Add a reminder to a capture and approve it to bring it here.</p> : data.followups.map(c => <div className="list-row" key={c.id}><div><strong>{c.details.person || c.details.company || "Follow-up"}</strong><p className="hint">{c.details.followup_on} · {c.details.channel}</p><a href={c.details.source_url} target="_blank" rel="noreferrer">Open source ↗</a></div><button className="secondary" disabled={busy} onClick={() => run(() => api(`/captures/${c.id}/followup-done`, "POST"))}>Clear reminder</button></div>)}<p className="hint">Clearing a reminder doesn’t log a sent follow-up. Capture the actual action in a session.</p></section><section className="panel discovery"><p className="eyebrow">A SOURCE TO EXPLORE</p><h2>Find something worth a conversation.</h2><p>daily.dev has an official MCP server and developer-news feeds. Open a story, select useful context, and capture it as research.</p><a className="secondary link-button" href="https://daily.dev/" target="_blank" rel="noreferrer">Explore daily.dev ↗</a><a className="text-button" href="https://docs.daily.dev/mcp-server/" target="_blank" rel="noreferrer">Official MCP setup</a><p className="hint">Manual source link, not a connected feed. Funding and contact details still need verification.</p></section></div>}
        {view === "today" && <section className="panel"><p className="eyebrow">ON YOUR HORIZON</p><h2>Upcoming follow-ups <span className="muted">{data.upcoming_followups.length}</span></h2>{data.upcoming_followups.length ? data.upcoming_followups.map(c => <div className="list-row" key={c.id}><div><strong>{c.details.person || c.details.company || "Follow-up"}</strong><p className="hint">{c.details.followup_on} · {c.details.channel}</p></div><a href={c.details.source_url} target="_blank" rel="noreferrer">Open source ↗</a></div>) : <p className="muted">No future reminders yet. Choose a follow-up date while capturing or reviewing; it appears here after approval.</p>}</section>}
      </>}
      <footer>Your pace. Your progress. Always private.</footer>
    </main></div>;
}
