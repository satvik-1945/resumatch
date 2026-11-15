"use client";
import { useEffect, useState, type CSSProperties } from "react";
import { api, duration, type ActivityMonth } from "@/lib/api";
import { blendColors, workflowStyle } from "@/lib/palette";

function shiftMonth(month: string, offset: number) {
  const [year, number] = month.split("-").map(Number);
  return new Date(Date.UTC(year, number - 1 + offset, 1)).toISOString().slice(0, 7);
}
const dayLabel = (date: string) => new Date(date + "T00:00:00Z").toLocaleDateString("en", { month: "long", day: "numeric", year: "numeric", timeZone: "UTC" });

export function ActivityCalendar({ revision, onOpen }: { revision: string; onOpen: (id: string) => void }) {
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const [activity, setActivity] = useState<ActivityMonth | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    api<ActivityMonth>(`/activity?month=${month}`).then(data => { if (active) { setActivity(data); setError(""); } })
      .catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [month, revision, retry]);
  const loading = activity?.month !== month;
  const day = activity?.days.find(d => d.date === selected);
  const first = (new Date(month + "-01T00:00:00Z").getUTCDay() + 6) % 7;
  const monthLabel = new Date(month + "-01T00:00:00Z").toLocaleDateString("en", { month: "long", year: "numeric", timeZone: "UTC" });
  function navigate(offset: number) { setMonth(m => shiftMonth(m, offset)); setSelected(null); }
  return <section className="activity-calendar panel" aria-label="Activity calendar">
    <header className="calendar-heading"><div><p className="eyebrow">THE DAYS YOU SHOWED UP</p><h2>Keep the rhythm.</h2><p className="muted">Small sessions become a body of work.</p></div><div className="calendar-month"><button className="icon-button" aria-label="Previous month" onClick={() => navigate(-1)}>‹</button><h3 aria-live="polite">{monthLabel}</h3><button className="icon-button" aria-label="Next month" onClick={() => navigate(1)}>›</button></div></header>
    {error ? <div className="error" role="alert">{error}<button className="text-button" onClick={() => setRetry(r => r + 1)}>Retry calendar</button></div> : loading ? <p role="status" className="muted">Loading activity…</p> : <>
      <div className="calendar-weekdays" aria-hidden="true">{["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map(d => <span key={d}>{d}</span>)}</div>
      <div className="calendar-grid" role="group" aria-label={monthLabel}>
        {Array.from({ length: first }, (_, i) => <span className="calendar-spacer" key={`pad-${i}`} />)}
        {activity!.days.map(d => {
          const colors = d.runs.map(r => r.color);
          const names = [...new Set(d.runs.map(r => r.workflow_name))];
          const future = d.date > activity!.today;
          const label = `${dayLabel(d.date)} — ${d.runs.length ? `${d.runs.length} completed ${d.runs.length === 1 ? "run" : "runs"}, ${d.approved_records} approved records. ${names.join("; ")}` : future ? "Future date" : "No completed activity"}`;
          const style = { "--day-wash": blendColors(colors, "18"), "--day-colors": blendColors(colors) } as CSSProperties;
          return <button type="button" key={d.date} data-date={d.date} className={`calendar-day ${d.runs.length ? "has-activity" : "quiet"} ${d.date === activity!.today ? "is-today" : ""}`} style={style} disabled={future} aria-label={label} aria-pressed={selected === d.date} onClick={() => setSelected(d.date)} title={label}>
            <span className="day-number">{Number(d.date.slice(-2))}</span><span className="day-count" aria-hidden="true">{d.runs.length ? `${d.runs.length} ${d.runs.length === 1 ? "run" : "runs"}` : "·"}</span><span className="day-color-band" aria-hidden="true" />
          </button>;
        })}
      </div>
      <div className="calendar-footer"><div className="calendar-totals"><span><strong>{activity!.summary.active_days}</strong> active days</span><span><strong>{activity!.summary.completed_runs}</strong> completed runs</span><span><strong>{activity!.summary.approved_records}</strong> approved records</span></div><div className="calendar-legend">{activity!.workflows.map(w => <span key={w.id} style={workflowStyle(w.color)}><i className="color-dot" />{w.name}</span>)}</div></div>
      {selected && <div className="calendar-detail" aria-live="polite"><div className="panel-heading"><h3>{dayLabel(selected)}</h3><button className="text-button" onClick={() => setSelected(null)}>Close day</button></div>{day?.runs.length ? day.runs.map(r => <button className="history-row" key={r.id} style={workflowStyle(r.color)} onClick={() => onOpen(r.id)}><span className="history-name"><i className="color-dot" /><span><strong>{r.run_name}</strong><small>{r.workflow_name}</small></span></span><span>{r.approved_records} approved<small>{duration(r.session_seconds)} session time</small></span><span aria-hidden="true">↗</span></button>) : <p className="muted">No completed session with approved records on this day. A quiet day is just a quiet day.</p>}</div>}
      <p className="calendar-note">UTC · Plotted on the run’s start date after completion. Pending and discarded records never light up a day. Multiple workflows blend their colors.</p>
    </>}
  </section>;
}
