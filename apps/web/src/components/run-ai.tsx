"use client";
import { useEffect, useRef, useState } from "react";
import { api, rawText, type Capture, type Session, type WorkflowAnalysis } from "@/lib/api";

export function RunAI({ session, refresh, hasUnsavedEdits = false, onBusyChange }: {
  session: Session; refresh: () => Promise<void>; hasUnsavedEdits?: boolean; onBusyChange?: (busy: boolean) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");
  const stop = useRef(false);
  useEffect(() => () => { stop.current = true; onBusyChange?.(false); }, [onBusyChange]);
  const eligible = session.captures?.filter(c => c.decision === "pending" && rawText(c.details)) || [];
  async function process() {
    if (hasUnsavedEdits || busy) return;
    onBusyChange?.(true);
    setBusy(true); setError(""); stop.current = false;
    let completed = 0, flagged = 0;
    try {
      for (const c of eligible) {
        if (stop.current) break;
        setProgress(`Processing ${completed + 1} of ${eligible.length}…`);
        const result = await api<{ capture: Capture }>(`/sessions/${session.id}/captures/${c.id}/process-ai`, "POST");
        completed++;
        const analysis = result.capture.analysis as WorkflowAnalysis | undefined;
        // Only a provider failure (key, quota, network) stops the pass; retrying would just fail
        // again and may charge. A rejected answer for one record is flagged and the pass continues.
        if (analysis?.failure === "provider") {
          setError(analysis.warning || "AI is unavailable. Local results were saved; processing stopped.");
          break;
        }
        if (analysis?.method !== "llm" || analysis.rejected_fields?.length) flagged++;
        if (completed % 5 === 0) await refresh();
      }
      setProgress(`${completed} of ${eligible.length} records processed${flagged ? ` · ${flagged} had AI values skipped because they weren’t found in the raw text` : ""}${stop.current ? " · stopped after current record" : ""}. Review filled fields before approving.`);
      await refresh();
    } catch (e) { setError((e as Error).message); await refresh(); }
    finally { setBusy(false); onBusyChange?.(false); }
  }
  if (session.state === "completed") return null;
  return <section className="run-ai"><div><p className="eyebrow">WORKFLOW FIELD CONTRACT · V{session.workflow_version}</p><h3>Raw text in. Structured records out.</h3><p className="hint">{eligible.length} pending records have saved raw text. Fills empty fields only. Saved manual values—including zero and No—are kept on every run.</p>{hasUnsavedEdits && <p className="notice">Save or cancel your unsaved capture edits before processing with AI. For a new record, use Capture &amp; process with AI.</p>}</div><div><button className="primary" disabled={busy || hasUnsavedEdits || !eligible.length} onClick={process}>{busy ? "Processing…" : "Process with AI"}</button>{busy && <button className="text-button" onClick={() => { stop.current = true; }}>Stop after current</button>}</div>{progress && <p role="status" className="ai-progress">{progress}</p>}{error && <p role="alert" className="error">{error}</p>}</section>;
}
