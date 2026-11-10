"use client";
import { useRef, useState, type FormEvent } from "react";
import { actionLabels, api, blank, type Capture, type Details } from "@/lib/api";
import { SourceAnalysis } from "./source-analysis";

export function CaptureForm({ sessionId, capture, editing = false, onSaved }: { sessionId: string; capture?: Capture; editing?: boolean; onSaved: () => Promise<void> }) {
  const [value, setValue] = useState<Details>(capture?.details ?? { ...blank });
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const requestId = useRef<string | null>(null);
  function field<K extends keyof Details>(key: K, val: Details[K]) { setValue(v => ({ ...v, [key]: val })); setSuccess(""); }
  async function save(event?: FormEvent<HTMLFormElement>, discard = false) {
    event?.preventDefault(); setBusy(true); setError(""); setSuccess("");
    try {
      if (capture) {
        if (editing) await api(`/sessions/${sessionId}/captures/${capture.id}`, "PUT", { details: value });
        else await api(`/sessions/${sessionId}/captures/${capture.id}/review`, "POST", {
          decision: discard ? "discarded" : "approved", details: discard ? capture.details : value, confirmed_action: confirmed,
        });
      } else {
        requestId.current ??= crypto.randomUUID();
        await api(`/sessions/${sessionId}/captures`, "POST", { request_id: requestId.current, details: value });
        requestId.current = null; setValue({ ...blank }); setSuccess("Captured for review. It does not count until approved.");
      }
      await onSaved();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  const needsConfirmation = ["sent", "followed_up", "replied"].includes(value.action);
  return <form className="capture-form" onSubmit={save}>
    {error && <p className="error" role="alert">{error}</p>}
    <fieldset disabled={busy}><div className="form-grid">
      <label className="wide">Source URL<input type="url" required maxLength={2000} value={value.source_url} placeholder="https://www.linkedin.com/in/…" onChange={e => field("source_url", e.target.value)} /></label>
      <label>Person <span className="optional">optional until contact confirmed</span><input maxLength={200} value={value.person} placeholder="Name, if known" onChange={e => field("person", e.target.value)} /></label>
      <label>Company <span className="optional">optional</span><input maxLength={200} value={value.company} placeholder="Company, if known" onChange={e => field("company", e.target.value)} /></label>
      <label>Action<select aria-label="Action" value={value.action} onChange={e => { field("action", e.target.value as Details["action"]); setConfirmed(false); }}>{Object.entries(actionLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <label>Channel<select value={value.channel} onChange={e => field("channel", e.target.value as Details["channel"])}><option value="linkedin">LinkedIn</option><option value="email">Email</option><option value="x">X / Twitter</option><option value="web">Website / news</option><option value="other">Other</option></select></label>
      <label className="wide">Note <span className="optional">why this matters / next step</span><textarea rows={2} maxLength={2000} value={value.notes} onChange={e => field("notes", e.target.value)} placeholder="What caught your attention? What should happen next?" /></label>
      <label>Follow-up reminder<input type="date" value={value.followup_on ?? ""} onChange={e => field("followup_on", e.target.value || null)} /></label>
      <label>Activity time <span className="optional">defaults to capture time</span><input type="datetime-local" value={value.occurred_at ? localDate(value.occurred_at) : ""} onChange={e => field("occurred_at", e.target.value ? new Date(e.target.value).toISOString() : null)} /></label>
    </div>
    <details open={!!capture && !editing}><summary>Source text & analysis</summary><label>Page title<input maxLength={500} value={value.source_title} onChange={e => field("source_title", e.target.value)} /></label><label>Source text<textarea aria-label="Source text" rows={5} maxLength={4000} value={value.quote} onChange={e => field("quote", e.target.value)} placeholder="Paste relevant text you are entitled to process. Names/company facts can be suggested during review." /></label></details>
    {capture && !editing && <SourceAnalysis sessionId={sessionId} captureId={capture.id} source={value.quote} initial={capture.analysis} disabled={busy} onUse={field} />}
    {capture && !editing && needsConfirmation && <label className="check"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />I confirm this action actually happened with the named person. This is my record, not platform-verified delivery.</label>}
    <div className="button-row"><button className="primary" disabled={busy || (!!capture && !editing && needsConfirmation && (!confirmed || !value.person.trim()))}>{busy ? "Saving…" : editing ? "Save capture changes" : capture ? "Approve record" : "Capture for review"}</button>
      {capture && !editing && <button className="secondary" type="button" disabled={busy} onClick={() => save(undefined, true)}>Discard</button>}</div>
    </fieldset>{success && <p role="status" className="success">{success}</p>}
  </form>;
}
function localDate(iso: string) {
  const d = new Date(iso);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
