"use client";
import { useState, type FormEvent } from "react";
import { api, actionLabels, duration, type Workflow, type WorkflowWrite, type WorkflowField, type Consolidated } from "@/lib/api";

export function WorkflowHub({ workflows, refresh, onRun, onOpen }: {
  workflows: Workflow[]; refresh: () => Promise<void>; onRun: (workflow: Workflow) => void; onOpen: (id: string) => void;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const [editor, setEditor] = useState<WorkflowWrite | null>(null);
  const [editId, setEditId] = useState<string | null>(null);
  const [records, setRecords] = useState<Consolidated | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const current = workflows.find(w => w.id === selected);
  async function create(kind: string) {
    setError(""); setBusy(true);
    try {
      const templates = await api<WorkflowWrite[]>("/workflow-templates");
      const value = structuredClone(templates.find(t => t.kind === kind) || templates[0]);
      if (kind === "custom") { value.kind = "custom"; value.name = "New workflow"; value.description = ""; value.fields = value.fields.filter(f => ["contact_url", "person", "company"].includes(f.key)); }
      setEditor(value); setEditId(null);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function save(event: FormEvent) {
    event.preventDefault(); if (!editor) return; setError(""); setBusy(true);
    try {
      const w = await api<Workflow>(`/workflows${editId ? `/${editId}` : ""}`, editId ? "PUT" : "POST", editor);
      await refresh(); setSelected(w.id); setEditor(null); setRecords(null);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  function updateField(index: number, values: Partial<WorkflowField>) {
    setEditor(e => e ? { ...e, fields: e.fields.map((field, i) => i === index ? { ...field, ...values } : field) } : e);
  }
  async function contract() {
    if (!current) return; setBusy(true); setError("");
    try {
      const data = await api(`/workflows/${current.id}/contract`);
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const a = document.createElement("a"); a.href = url; a.download = `workflow-${current.id}-v${current.version}.json`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <>
    <header className="section-title"><p className="eyebrow">ONE INTENTION. MANY DAYS OF PROGRESS.</p><h1>Your workflows.</h1><p className="lede">Keep the same purpose and fields. Run it again tomorrow, and see your contacts together.</p></header>
    {error && <div className="error" role="alert">{error}</div>}
    {editor ? <form className="panel workflow-editor" onSubmit={save}>
      <div className="panel-heading"><h2>{editId ? "Edit workflow" : "Create a workflow"}</h2><button className="text-button" type="button" onClick={() => setEditor(null)}>Cancel</button></div>
      <fieldset disabled={busy}><div className="form-grid"><label>Workflow name<input required maxLength={200} value={editor.name} onChange={e => setEditor({ ...editor, name: e.target.value })} /></label><label>Description<input maxLength={1000} value={editor.description} onChange={e => setEditor({ ...editor, description: e.target.value })} /></label></div>
      <h3>Your record fields</h3><p className="hint">Contact URL, Name and Company stay available. Add whatever else this workflow needs. AI instructions tell the extractor what to look for; unknowns remain empty.</p>
      {editor.fields.map((field, index) => {
        const essential = ["contact_url", "person", "company"].includes(field.key);
        const existingKey = !!editId && !!workflows.find(w => w.id === editId)?.fields.some(f => f.key === field.key);
        return <div className="field-definition" key={index}>
          <label>Field label<input required value={field.label} maxLength={100} onChange={e => updateField(index, { label: e.target.value })} /></label>
          <label>Field key<input required value={field.key} pattern="[a-z][a-z0-9_]{0,39}" disabled={existingKey || essential} onChange={e => updateField(index, { key: e.target.value })} /></label>
          <label>Type<select value={field.type} disabled={essential} onChange={e => updateField(index, { type: e.target.value as WorkflowField["type"] })}>{["text", "long_text", "number", "boolean", "date", "url"].map(type => <option key={type} value={type}>{type.replace("_", " ")}</option>)}</select></label>
          <label className="field-instruction">AI extraction instruction<input value={field.instruction || ""} maxLength={500} onChange={e => updateField(index, { instruction: e.target.value })} placeholder="Extract only when explicitly supported by the pasted text" /></label>
          {!essential && <button className="text-button" type="button" onClick={() => setEditor({ ...editor, fields: editor.fields.filter((_, i) => i !== index) })}>Remove {field.label}</button>}
        </div>;
      })}
      <button className="secondary" type="button" disabled={editor.fields.length >= 20} onClick={() => { let n = editor.fields.length; while (editor.fields.some(f => f.key === `field_${n}`)) n++; setEditor({ ...editor, fields: [...editor.fields, { key: `field_${n}`, label: "New field", type: "text", instruction: "" }] }); }}>+ Add field</button>
      <p className="hint">Saving generates a versioned DSL, prompt, JSON output schema and JSONata mapping. Existing runs keep their version until you explicitly update their fields.</p><button className="primary">{busy ? "Saving…" : "Save workflow"}</button></fieldset>
    </form> : <>
      <div className="workflow-toolbar"><button className="primary" disabled={busy} onClick={() => create("founder_connections")}>Create workflow</button><button className="secondary" disabled={busy} onClick={() => create("contact_outreach")}>Use contact outreach template</button><button className="text-button" disabled={busy} onClick={() => create("custom")}>Start with only contact fields</button></div>
      <div className="workflow-cards">{workflows.map(w => <button className={`workflow-card ${selected === w.id ? "selected" : ""}`} key={w.id} onClick={() => { setSelected(w.id); setRecords(null); }}><span className="pill">{w.runs.length} dated runs</span><h2>{w.name}</h2><p>{w.description}</p><div><strong>{w.record_count}</strong> records <span>· {w.approved_count} approved</span></div><small>Open workflow ↗</small></button>)}</div>
      {!workflows.length && <section className="panel empty"><h2>Give your outreach a home.</h2><p>Create a workflow once. Each session becomes a dated run inside it.</p></section>}
      {current && <section className="panel"><div className="workflow-title"><div><p className="eyebrow">PARENT WORKFLOW · FIELDS V{current.version}</p><h2>{current.name}</h2></div><div className="button-row"><button className="primary" onClick={() => onRun(current)}>Start a run</button><button className="secondary" disabled={busy} onClick={async () => { setBusy(true); setError(""); try { setRecords(await api(`/workflows/${current.id}/records`)); } catch (e) { setError((e as Error).message); } finally { setBusy(false); } }}>Consolidated records</button><button className="text-button" onClick={() => { setEditId(current.id); setEditor({ name: current.name, description: current.description, kind: current.kind, fields: structuredClone(current.fields), expected_version: current.version }); }}>Edit fields & name</button><button className="text-button" disabled={busy} onClick={contract}>Download DSL & JSONata</button></div></div>
      <div className="field-chips">{current.fields.map(f => <span key={f.key}>{f.label}</span>)}</div>
      {records ? <><h3>All contacts in this workflow</h3><p className="hint">{records.contact_count} normalized contacts across {records.record_count} records. Pending entries are labeled; discarded records are excluded. Repeated contacts across dates share a row.</p><div className="records-scroll"><table className="records-table"><thead><tr><th>Contact</th><th>Company</th>{current.fields.filter(f => !["contact_url", "person", "company"].includes(f.key)).map(f => <th key={f.key}>{f.label}</th>)}<th>Runs & recorded actions</th></tr></thead><tbody>{records.contacts.map(row => <tr key={row.contact_key}><td><a href={row.contact_url} target="_blank" rel="noreferrer">{row.person || "Name not recorded"} ↗</a></td><td>{row.company || "—"}</td>{current.fields.filter(f => !["contact_url", "person", "company"].includes(f.key)).map(f => <td key={f.key}>{row.fields[f.key] == null ? "—" : String(row.fields[f.key])}</td>)}<td>{row.entries.map(entry => <button className="record-run-link" key={entry.capture_id} onClick={() => onOpen(entry.run_id)}>{entry.run_name} · {actionLabels[entry.action]} · {entry.decision}</button>)}</td></tr>)}</tbody></table>{!records.contacts.length && <p className="empty">No records in this workflow yet.</p>}</div></> : <><h3>Dated runs</h3>{current.runs.map(run => <button className="history-row" key={run.id} onClick={() => onOpen(run.id)}><span><strong>{run.run_name}</strong><small>{new Date(run.started_at).toLocaleString()} · {run.state}</small></span><span>{run.record_count} records<small>{duration(run.elapsed_seconds)} session time</small></span><span>↗</span></button>)}{!current.runs.length && <p className="muted">Start the first run when you’re ready.</p>}</>}
      </section>}
    </>}
  </>;
}
