"use client";
import { useState } from "react";
import { api, type AiRunSummary } from "@/lib/api";

// Rating one AI run. Ratings + notes are what prompt changes get judged against in the AI monitor.
export function AiFeedback({ runId, rating: initialRating = null, feedback: initialNote = "" }: { runId: string; rating?: -1 | 1 | null; feedback?: string }) {
  const [rating, setRating] = useState(initialRating);
  const [note, setNote] = useState(initialNote);
  const [saved, setSaved] = useState(initialNote);
  const [error, setError] = useState("");
  async function save(nextRating: -1 | 0 | 1, nextNote = note) {
    setError("");
    try {
      const run = await api<AiRunSummary>(`/ai-runs/${runId}/feedback`, "PUT", { rating: nextRating, feedback: nextNote });
      setRating(run.rating); setSaved(run.feedback);
    } catch (e) { setError((e as Error).message); }
  }
  return <div className="ai-feedback" aria-label="Rate this AI result" role="group">
    <span className="hint">Useful?</span>
    <button type="button" aria-pressed={rating === 1} className={rating === 1 ? "active" : ""} onClick={() => void save(rating === 1 ? 0 : 1)}>👍</button>
    <button type="button" aria-pressed={rating === -1} className={rating === -1 ? "active" : ""} onClick={() => void save(rating === -1 ? 0 : -1)}>👎</button>
    {rating !== null && <form onSubmit={e => { e.preventDefault(); void save(rating, note); }}>
      <input aria-label="What should be better?" maxLength={2000} value={note} onChange={e => setNote(e.target.value)} placeholder={rating === -1 ? "What was wrong?" : "What worked? (optional)"} />
      <button className="secondary" disabled={note.trim() === saved}>Save note</button></form>}
    {error && <p className="error" role="alert">{error}</p>}
  </div>;
}
