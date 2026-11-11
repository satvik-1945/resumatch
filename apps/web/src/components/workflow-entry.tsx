"use client";
import { useCallback, useState } from "react";
import { api, type Overview, type Session, type Workflow } from "@/lib/api";
import { CaptureForm } from "@/components/capture-form";
import { RunAI } from "@/components/run-ai";

// Manual entry from the consolidated view. Records always belong to a run, so this adds to the
// workflow's open run (or starts one on an explicit click); it never bypasses run state rules.
export function WorkflowEntry({ workflow, onChanged, onOpen }: {
  workflow: Workflow; onChanged: () => Promise<void>; onOpen: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState<Session | null | undefined>(undefined);
  const [dirty, setDirty] = useState<Set<string>>(() => new Set());
  const [aiBusy, setAiBusy] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    const overview = await api<Overview>("/overview");
    setCurrent(overview.current ? await api<Session>(`/sessions/${overview.current.id}`) : null);
  }, []);
  const trackDirty = useCallback((id: string, next: boolean) => {
    setDirty(previous => {
      if (previous.has(id) === next) return previous;
      const copy = new Set(previous); if (next) copy.add(id); else copy.delete(id); return copy;
    });
  }, []);
  async function act(work: () => Promise<unknown>) {
    setBusy(true); setError("");
    try { await work(); await load(); await onChanged(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  const saved = async () => { await load(); await onChanged(); };
  const mine = current && current.workflow_id === workflow.id ? current : null;
  if (!open) return <button className="secondary" onClick={() => { setOpen(true); setError(""); setCurrent(undefined); void load().catch(e => setError((e as Error).message)); }}>+ Add a record manually</button>;
  return <section className="workflow-entry">
    <div className="panel-heading"><h3>Add a record manually</h3><button className="text-button" disabled={aiBusy || dirty.size > 0} onClick={() => setOpen(false)}>Close</button></div>
    {error && <p className="error" role="alert">{error}</p>}
    {current === undefined ? <p className="hint" role="status">Checking your open run…</p>
      : current && !mine ? <p className="notice">Your open run “{current.run_name}” belongs to {current.workflow_name}. Finish it before adding records here.</p>
      : !mine ? <><p className="hint">Records belong to a run. Starting one uses the next name ({workflow.next_run_name}) and starts its session timer.</p><button className="primary" disabled={busy} onClick={() => act(() => api("/sessions", "POST", { workflow_id: workflow.id, intention: "Manual entries", target_minutes: 25 }))}>Start a run for manual entries</button></>
      : mine.state === "paused" ? <><p className="hint">“{mine.run_name}” is paused.</p><button className="primary" disabled={busy} onClick={() => act(() => api(`/sessions/${mine.id}/transition`, "POST", { action: "resume" }))}>Resume run to add records</button></>
      : mine.state === "review" ? <><p className="notice">“{mine.run_name}” is in review, so it can’t take new records. Complete the review, then start a new run.</p><button className="secondary" onClick={() => onOpen(mine.id)}>Open review</button></>
      : <><p className="hint">Adding to “{mine.run_name}”. Paste raw text and leave unknown fields blank; Process with AI fills only empty fields. Nothing counts until you approve it in review.</p>
        <CaptureForm sessionId={mine.id} fields={mine.field_definition} locked={aiBusy} onDirtyChange={trackDirty} onSaved={saved} />
        <RunAI key={mine.id} session={mine} hasUnsavedEdits={dirty.size > 0} onBusyChange={setAiBusy} refresh={saved} />
        <button className="text-button" onClick={() => onOpen(mine.id)}>Open this run</button></>}
  </section>;
}
