"use client";
import { useState } from "react";
import { api, type SourceAnalysis as Analysis } from "@/lib/api";

export function SourceAnalysis({ sessionId, captureId, source, initial, disabled, onUse }: {
  sessionId: string; captureId: string; source: string; initial?: Analysis | null; disabled: boolean;
  onUse: (field: "person" | "company" | "notes", value: string) => void;
}) {
  const [result, setResult] = useState<Analysis | null>(initial ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function analyze() {
    setBusy(true); setError("");
    try { setResult(await api<Analysis>(`/sessions/${sessionId}/captures/${captureId}/analyze`, "POST", { source_text: source })); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  const stale = !!result && result.source_text !== source;
  return <section className="analysis-panel" aria-label="Source analysis">
    <div className="analysis-heading"><div><span className="eyebrow">TURN SOURCE TEXT INTO SUGGESTIONS</span><h3>Let AI help with the details</h3></div><button type="button" className="secondary" disabled={disabled || busy || !source.trim()} onClick={analyze}>{busy ? "Analyzing source…" : "Analyze source text"}</button></div>
    <p className="hint">Sends only the source text above to your configured provider when clicked. Review suggestions before using them. Actions and follow-up dates stay under your control.</p>
    {error && <p className="error" role="alert">{error}</p>}
    {result && <><p className="hint">{result.method === "llm" ? `AI suggestions · ${result.model}` : "Local suggestions · not an AI response"}</p>{result.warning && <p className="notice">{result.warning}</p>}{stale && <p className="notice">The source text changed. Analyze it again before using these suggestions.</p>}
      <div className="suggestion-grid">{(["person", "company", "role"] as const).map(key => {
        const fact = result.suggestions[key];
        return <div className="suggestion" key={key}><span className="eyebrow">{key === "person" ? "NAME" : key.toUpperCase()}</span><strong>{fact?.value || "Not established from source"}</strong>{fact && <><blockquote>{fact.source_quote}</blockquote>{key !== "role" && <button type="button" className="text-button" disabled={disabled || stale} onClick={() => onUse(key, fact.value)}>Use {key === "person" ? "name" : "company"} in form</button>}</>}</div>;
      })}</div>
      {result.suggestions.key_points.length > 0 && <div className="suggestion"><h4>Useful source points</h4><ul>{result.suggestions.key_points.map((fact, i) => <li key={i}>{fact.value}<blockquote>{fact.source_quote}</blockquote></li>)}</ul><button type="button" className="text-button" disabled={disabled || stale} onClick={() => onUse("notes", result.suggestions.key_points.map(f => f.value).join("\n").slice(0, 2000))}>Use source points as note</button></div>}
      <p className="hint">Using a suggestion edits this form only. It does not approve or save the record.</p>
    </>}
  </section>;
}
