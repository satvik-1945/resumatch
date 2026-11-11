"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { actionLabels, api, blank, confirmedActions, processCapture, rawText, type Capture, type Details, type WorkflowField } from "@/lib/api";

function editable(details: Details): Details {
  return { ...details, notes: rawText(details), quote: "", fields: { ...details.fields } };
}

export function CaptureForm({ sessionId, capture, editing = false, fields = [], compact = false, locked = false, onDirtyChange, onSaved }: {
  sessionId: string; capture?: Capture; editing?: boolean; fields?: WorkflowField[]; compact?: boolean; locked?: boolean;
  onDirtyChange?: (id: string, dirty: boolean) => void; onSaved: () => Promise<void>;
}) {
  const [processing, setProcessing] = useState(false);
  const incoming = JSON.stringify(capture?.details ?? blank);
  const [stored, setStored] = useState(incoming);
  const [dirty, setDirty] = useState(false);
  const [value, setValue] = useState<Details>(() => editable(capture?.details ?? blank));
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const requestId = useRef<string | null>(null);
  const formId = `${sessionId}:${capture?.id ?? "new"}`;
  useEffect(() => () => onDirtyChange?.(formId, false), [formId, onDirtyChange]);
  // Refresh clean forms when processing returns, even if a fallback retry has the same source
  // hash. Never remount or replace an unsaved manual draft during polling.
  if (stored !== incoming && !dirty && !busy) {
    setStored(incoming); setValue(editable(capture?.details ?? blank)); setConfirmed(false);
  }
  function markDirty(next: boolean) { setDirty(next); onDirtyChange?.(formId, next); }
  function field<K extends keyof Details>(key: K, val: Details[K]) {
    const next = { ...value, [key]: val };
    setValue(next); markDirty(JSON.stringify(next) !== JSON.stringify(editable(JSON.parse(stored)))); setSuccess("");
  }
  async function save(event?: FormEvent<HTMLFormElement>, discard = false) {
    event?.preventDefault();
    // "Capture & process with AI" submits the same form, so browser validation still applies.
    const thenProcess = !capture && (event?.nativeEvent as SubmitEvent | undefined)?.submitter?.dataset.process === "1";
    if (thenProcess && !value.notes.trim()) { setError("Paste raw capture text so AI has something to process."); return; }
    setBusy(true); setError(""); setSuccess("");
    try {
      if (capture) {
        if (editing) await api(`/sessions/${sessionId}/captures/${capture.id}`, "PUT", { details: value });
        else await api(`/sessions/${sessionId}/captures/${capture.id}/review`, "POST", {
          decision: discard ? "discarded" : "approved", details: discard ? capture.details : value, confirmed_action: confirmed,
        });
      } else {
        requestId.current ??= crypto.randomUUID();
        const created = await api<Capture>(`/sessions/${sessionId}/captures`, "POST", { request_id: requestId.current, details: value });
        requestId.current = null; setValue({ ...blank, fields: {} }); markDirty(false);
        setSuccess("Captured for review. It does not count until approved.");
        if (thenProcess) {
          setProcessing(true); await onSaved();
          setSuccess(`Captured for review. ${await processCapture(sessionId, created.id)}`);
        }
      }
      await onSaved();
      markDirty(false);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); setProcessing(false); }
  }
  async function saveDraft() {
    if (!capture) return;
    setBusy(true); setError("");
    try { await api(`/sessions/${sessionId}/captures/${capture.id}`, "PUT", { details: value }); await onSaved(); markDirty(false); setSuccess("Draft changes saved. You can now process this raw text with AI."); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  const needsConfirmation = confirmedActions.includes(value.action);
  const form = <form className="capture-form" onSubmit={save}>
    {error && <p className="error" role="alert">{error}</p>}
    {dirty && <p className="hint">Unsaved manual changes. Save or cancel editing before processing with AI.</p>}
    <fieldset disabled={busy || locked}>
    <label>Raw capture text<textarea aria-label="Raw capture text" rows={5} maxLength={16000} value={value.notes} onChange={e => field("notes", e.target.value)} placeholder="Paste the profile snippet, conversation context, or your rough notes here. Process with AI fills this workflow’s fields." /><span className="hint">One input for the rough material. Keep the contact URL; other details can be filled by AI or edited below.</span></label>
    <div className="form-grid">
      <label className="wide">Contact URL<input type="url" required maxLength={2000} value={value.source_url} placeholder="https://www.linkedin.com/in/…" onChange={e => field("source_url", e.target.value)} /></label>
      <label>Name<input aria-label="Name" maxLength={200} value={value.person} placeholder="AI can fill this from your raw text" onChange={e => field("person", e.target.value)} /></label>
      <label>Company<input aria-label="Company" maxLength={200} value={value.company} placeholder="Unknown is okay" onChange={e => field("company", e.target.value)} /></label>
      {fields.filter(f => !["contact_url", "person", "company"].includes(f.key)).map(f => {
        const current = value.fields?.[f.key];
        function update(next: string | number | boolean | null) { field("fields", { ...value.fields, [f.key]: next }); }
        return <label key={f.key} className={f.type === "long_text" ? "wide" : ""}>{f.label}{f.type === "boolean" ? <select aria-label={f.label} value={current == null ? "" : String(current)} onChange={e => update(e.target.value === "" ? null : e.target.value === "true")}><option value="">Unknown</option><option value="true">Yes</option><option value="false">No</option></select> : f.type === "long_text" ? <textarea aria-label={f.label} rows={2} maxLength={4000} value={String(current ?? "")} onChange={e => update(e.target.value || null)} /> : <input aria-label={f.label} type={f.type === "number" ? "number" : f.type === "date" ? "date" : f.type === "url" ? "url" : "text"} step={f.type === "number" ? "any" : undefined} maxLength={200} value={String(current ?? "")} onChange={e => update(e.target.value === "" ? null : f.type === "number" ? Number(e.target.value) : e.target.value)} />}</label>;
      })}
      <label>Action<select aria-label="Action" value={value.action} onChange={e => { field("action", e.target.value as Details["action"]); setConfirmed(false); }}>{Object.entries(actionLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <label>Channel<select value={value.channel} onChange={e => field("channel", e.target.value as Details["channel"])}><option value="linkedin">LinkedIn</option><option value="email">Email</option><option value="x">X / Twitter</option><option value="web">Website / news</option><option value="other">Other</option></select></label>
      <label>Follow-up reminder<input type="date" value={value.followup_on ?? ""} onChange={e => field("followup_on", e.target.value || null)} /></label>
      <label>Activity time<input type="datetime-local" value={value.occurred_at ? localDate(value.occurred_at) : ""} onChange={e => field("occurred_at", e.target.value ? new Date(e.target.value).toISOString() : null)} /></label>
    </div>
    {capture && !editing && needsConfirmation && <label className="check"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />I confirm this action actually happened with the named person. This is my record, not platform-verified delivery.</label>}
    <div className="button-row"><button className="primary" disabled={busy || (!!capture && !editing && needsConfirmation && (!confirmed || !value.person.trim()))}>{busy && !processing ? "Saving…" : editing ? "Save capture changes" : capture ? "Approve record" : "Capture for review"}</button>{!capture && <button className="secondary" data-process="1" disabled={busy}>{processing ? "Processing with AI…" : "Capture & process with AI"}</button>}
      {capture && !editing && <><button className="secondary" type="button" disabled={busy} onClick={saveDraft}>Save draft changes</button><button className="secondary" type="button" disabled={busy} onClick={() => save(undefined, true)}>Discard</button></>}</div>
    </fieldset>{success && <p role="status" className="success">{success}</p>}
  </form>;
  return capture && !editing ? <><div className="field-chips">{fields.filter(f => !["contact_url", "person", "company"].includes(f.key) && value.fields?.[f.key] != null).map(f => <span key={f.key}><strong>{f.label}:</strong> {String(value.fields?.[f.key])}</span>)}</div><details className="review-fields" open={!compact}><summary>Review fields & approve</summary>{form}</details></> : form;
}
function localDate(iso: string) {
  const d = new Date(iso);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
