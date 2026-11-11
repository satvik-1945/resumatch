"use client";
import { useEffect, useState } from "react";
import { AiFeedback } from "@/components/ai-feedback";
import { aiKindLabels, aiStatusLabels, api, type AiKind, type AiRunDetail, type AiRunSummary, type AiStatus, type AiVersion } from "@/lib/api";

const PAGE = 50;
const json = (value: unknown) => JSON.stringify(value, null, 2);
const statusTone: Record<AiStatus, string> = { ok: "approved", partial: "review", rejected: "pending", provider_error: "discarded", fetch_error: "discarded", error: "discarded" };

function RunDetail({ id }: { id: string }) {
  const [run, setRun] = useState<AiRunDetail | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api<AiRunDetail>(`/ai-runs/${id}`).then(setRun, e => setError((e as Error).message)); }, [id]);
  if (error) return <p className="error" role="alert">{error}</p>;
  if (!run) return <p className="hint" role="status">Loading run…</p>;
  const research = run.research as { company_url?: string; pages?: { url: string; chars: number }[]; error?: string } | null;
  return <div className="ai-run-detail">
    {run.error && <p className="error">{run.error}</p>}
    {research && <><h4>Research</h4>
      {research.company_url && <p>Company site: <a href={research.company_url} target="_blank" rel="noreferrer">{research.company_url}</a></p>}
      {research.error ? <p className="hint">Fetch failed: {research.error}</p> : <ul>{research.pages?.map(p => <li key={p.url}>{p.url} · {p.chars.toLocaleString()} chars read</li>)}</ul>}</>}
    {run.result != null && <><h4>Kept after grounding</h4><pre>{json(run.result)}</pre></>}
    {!!run.rejected.length && <><h4>Rejected · {run.rejected.length}</h4><pre>{json(run.rejected)}</pre></>}
    <details><summary>Raw model output</summary><pre>{json(run.output)}</pre></details>
    <details><summary>Input sent to the model</summary><pre>{json(run.input)}</pre></details>
    {run.prompt && <details><summary>Prompt version {run.prompt.sha256.slice(0, 8)}</summary><pre>{run.prompt.instruction}</pre><pre>{json(run.prompt.output_schema)}</pre></details>}
    <AiFeedback runId={run.id} rating={run.rating} feedback={run.feedback} />
  </div>;
}

async function fetchMonitor(kind: AiKind | "", status: AiStatus | "", offset: number) {
  const query = new URLSearchParams({ limit: String(PAGE), offset: String(offset) });
  if (kind) query.set("kind", kind);
  if (status) query.set("status", status);
  const [stats, list] = await Promise.all([api<{ versions: AiVersion[] }>("/ai-runs/stats"), api<{ runs: AiRunSummary[] }>(`/ai-runs?${query}`)]);
  return { versions: stats.versions, runs: list.runs };
}

// Every AI generation, stored server-side: compare prompt versions, inspect inputs/outputs, rate results.
export function AiMonitor() {
  const [versions, setVersions] = useState<AiVersion[]>([]);
  const [runs, setRuns] = useState<AiRunSummary[] | null>(null);
  const [kind, setKind] = useState<AiKind | "">("");
  const [status, setStatus] = useState<AiStatus | "">("");
  const [offset, setOffset] = useState(0);
  const [open, setOpen] = useState("");
  const [error, setError] = useState("");
  const [refreshes, setRefreshes] = useState(0);
  useEffect(() => {
    fetchMonitor(kind, status, offset).then(data => { setVersions(data.versions); setRuns(data.runs); setError(""); }, e => setError((e as Error).message));
  }, [kind, status, offset, refreshes]);
  const failed = (v: AiVersion) => v.statuses.rejected + v.statuses.provider_error + v.statuses.fetch_error + v.statuses.error;
  return <>
    <header className="section-title"><p className="eyebrow">MAKE THE AI BETTER, ONE RUN AT A TIME</p><h1>AI monitor</h1><p className="lede">Every “AI” click is stored: what it researched, what it was sent, what the model returned, and what grounding kept or rejected. Rate results, change a prompt, then compare versions.</p></header>
    {error && <p className="error" role="alert">{error}</p>}
    <section className="panel"><div className="panel-heading"><h2>Prompt versions</h2><button className="secondary" onClick={() => setRefreshes(n => n + 1)}>Refresh</button></div>
      {!versions.length ? <p className="muted">No AI runs yet. Use Process with AI, Build my persona or Generate message brief.</p> :
        <div className="records-scroll"><table className="records-table"><thead><tr><th>Feature</th><th>Version</th><th>Runs</th><th>OK</th><th>Partly grounded</th><th>Failed</th><th>Avg time</th><th>Tokens in / out</th><th>👍 / 👎</th><th>Last used</th></tr></thead>
          <tbody>{versions.map(v => <tr key={`${v.kind}-${v.prompt_sha256}`}><td>{aiKindLabels[v.kind] ?? v.kind}</td><td><code>{v.prompt_sha256?.slice(0, 8) ?? "—"}</code></td><td>{v.runs}</td><td>{v.statuses.ok}</td><td>{v.statuses.partial}</td><td>{failed(v)}</td>
            <td>{v.avg_latency_ms == null ? "—" : `${(v.avg_latency_ms / 1000).toFixed(1)}s`}</td><td>{(v.prompt_tokens ?? 0).toLocaleString()} / {(v.completion_tokens ?? 0).toLocaleString()}</td><td>{v.thumbs_up} / {v.thumbs_down}</td><td>{new Date(v.last_at).toLocaleString()}</td></tr>)}</tbody></table></div>}
    </section>
    <section className="panel"><div className="panel-heading"><h2>Runs</h2><span className="hint">Newest first</span></div>
      <div className="filter-chips" role="group" aria-label="Filter by feature">{(["", ...Object.keys(aiKindLabels)] as (AiKind | "")[]).map(k => <button key={k || "all"} type="button" aria-pressed={kind === k} className={kind === k ? "active" : ""} onClick={() => { setKind(k); setOffset(0); }}>{k ? aiKindLabels[k] : "All features"}</button>)}</div>
      <div className="filter-chips" role="group" aria-label="Filter by status">{(["", ...Object.keys(aiStatusLabels)] as (AiStatus | "")[]).map(s => <button key={s || "all"} type="button" aria-pressed={status === s} className={status === s ? "active" : ""} onClick={() => { setStatus(s); setOffset(0); }}>{s ? aiStatusLabels[s] : "Any status"}</button>)}</div>
      {runs && !runs.length && <p className="muted">No runs match.</p>}
      {runs?.map(r => <div className="ai-run" key={r.id}>
        <button className="history-row" aria-expanded={open === r.id} onClick={() => setOpen(open === r.id ? "" : r.id)}>
          <span><strong>{aiKindLabels[r.kind] ?? r.kind} <span className={`pill ${statusTone[r.status]}`}>{aiStatusLabels[r.status]}</span></strong>
            <small>{new Date(r.created_at).toLocaleString()} · {r.subject ?? "—"}{r.rejected_count ? ` · ${r.rejected_count} rejected` : ""}{r.rating === 1 ? " · 👍" : r.rating === -1 ? " · 👎" : ""}</small></span>
          <span>{r.latency_ms == null ? "—" : `${(r.latency_ms / 1000).toFixed(1)}s`}<small>{r.model ?? "no model"} · {r.prompt_sha256?.slice(0, 8) ?? "no prompt"}</small></span><span aria-hidden="true">{open === r.id ? "▾" : "▸"}</span></button>
        {open === r.id && <RunDetail id={r.id} />}
      </div>)}
      <div className="button-row"><button className="secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Newer</button><button className="secondary" disabled={(runs?.length ?? 0) < PAGE} onClick={() => setOffset(offset + PAGE)}>Older</button></div>
    </section>
  </>;
}
