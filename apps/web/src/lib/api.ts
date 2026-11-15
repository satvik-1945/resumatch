export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}
export async function api<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method, credentials: "same-origin", cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch { throw new ApiError("Cannot reach the API. Check your connection and retry.", 0); }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const message = typeof data.detail === "string" ? data.detail : data.detail?.message ? data.detail.message : Array.isArray(data.detail)
      ? data.detail.map((e: { msg: string }) => e.msg).join(". ") : "Request failed. Please retry.";
    throw new ApiError(message, response.status);
  }
  return response.status === 204 ? undefined as T : response.json();
}
export type User = { id: string; email: string; weekly_target: number };
export type Action = "researched" | "drafted" | "connection_requested" | "sent" | "followed_up" | "replied";
// Actions that only count after the user confirms they really happened; never bulk-approved.
export const confirmedActions: Action[] = ["connection_requested", "sent", "followed_up", "replied"];
export const actionLabels: Record<Action, string> = {
  researched: "Researched", drafted: "Drafted", connection_requested: "Connection request sent", sent: "Sent", followed_up: "Followed up", replied: "Reply received",
};
export type Details = {
  source_url: string; source_title: string; quote: string; person: string; company: string;
  channel: "linkedin" | "email" | "x" | "web" | "other";
  action: Action; notes: string; occurred_at: string | null; followup_on: string | null;
  fields?: Record<string, string | number | boolean | null>;
};
export type Capture = {
  id: string; details: Details; original: Details; source: "manual" | "browser";
  decision: "pending" | "approved" | "discarded"; created_at: string;
  reviewed_at: string | null; followup_done: boolean;
  duplicate_of?: string | null;
  same_raw_text_as?: string | null;
  analysis?: SourceAnalysis | WorkflowAnalysis | null;
};
export type Session = {
  id: string; intention: string; target_minutes: number;
  state: "active" | "paused" | "review" | "completed";
  elapsed_seconds: number; started_at: string; finished_at: string | null; completed_at: string | null;
  approved_count: number; pending_count: number; counts: Partial<Record<Action, number>>; captures?: Capture[];
  workflow_id: string; workflow_name: string; workflow_version: number; run_name: string; workflow_kind?: string;
  field_definition: WorkflowField[];
};
export type Overview = {
  current: Session | null; history: Session[]; followups: Capture[]; upcoming_followups: Capture[];
  week: { starts_at: string; sessions: number; target: number; counts: Partial<Record<Action, number>> };
};
export function duration(seconds: number) {
  return `${Math.floor(seconds / 60).toString().padStart(2, "0")}:${Math.floor(seconds % 60).toString().padStart(2, "0")}`;
}
export const blank: Details = {
  source_url: "", source_title: "", quote: "", person: "", company: "", channel: "linkedin",
  action: "researched", notes: "", occurred_at: null, followup_on: null,
};

export type SourceFact = { value: string; source_quote: string };
export type SourceAnalysis = {
  schema_version: 1; method: "llm" | "local"; model: string | null; analyzed_at: string;
  source_text: string; source_sha256: string; warning: string | null;
  suggestions: { person: SourceFact | null; company: SourceFact | null; role: SourceFact | null; key_points: SourceFact[] };
};
export type SessionRecap = {
  progress: {
    workflow_id: string; workflow_name: string; color: string; run_name: string; previous_runs: number;
    previous: { id: string; run_name: string; approved_records: number; session_seconds: number } | null;
    record_delta: number | null; time_delta_seconds: number | null; personal_best_records: boolean;
  };
  payload: {
    schema_version: 1; session_id: string; intention: string; generated_at: string; completed_at: string;
    session_seconds: number; target_minutes: number; approved_records: number; discarded_records: number;
    action_counts: Record<Action, number>; channel_counts: Record<string, number>;
    known_people: number; known_companies: number; unknown_person_records: number;
    highlights: string[]; limitations: string[];
    activities: { capture_id: string; action: Action; channel: string; person: string; company: string;
      source_url: string; notes: string; source_text: string; occurred_at: string; followup_on: string | null }[];
  };
  reflection: { method: "llm" | "local"; model: string | null; warning: string | null;
    observations: { capture_id: string; text: string; source_quote: string }[];
    reviewed_capture_ids: string[] } | null;
};

export type WorkflowField = { key: string; label: string; type: "text" | "long_text" | "number" | "boolean" | "date" | "url"; instruction: string };
export type WorkflowWrite = { name: string; description: string; kind: "founder_connections" | "contact_outreach" | "custom"; fields: WorkflowField[]; expected_version?: number; color?: string };
export type Workflow = WorkflowWrite & { id: string; color: string; version: number; record_count: number; approved_count: number; pending_count: number; next_run_name: string;
  runs: { id: string; run_name: string; intention: string; state: Session["state"]; started_at: string; elapsed_seconds: number; record_count: number; pending_count: number; approved_count: number; workflow_version: number }[] };
export type WorkflowAnalysis = { schema_version: 2; workflow_id: string; workflow_version: number; method: "llm" | "local";
  warning: string | null; model: string | null; source_text: string; source_sha256: string;
  fields: Record<string, { value: string | number | boolean; source_quote: string } | null>;
  filled_fields: string[]; preserved_fields: string[]; rejected_fields?: string[]; failure?: "provider" | "output" | null };
export type Consolidated = { contact_count: number; record_count: number; includes_pending: boolean; contacts: {
  contact_key: string; contact_url: string; person: string; company: string; fields: Record<string, string | number | boolean | null>;
  entries: { capture_id: string; run_id: string; run_name: string; decision: string; action: Action; occurred_at: string; followup_on: string | null }[];
}[] };
export function rawText(details: Details) {
  return (details.notes + (details.quote && !details.notes.includes(details.quote) ? `\n\n${details.quote}` : "")).trim();
}

// Runs the workflow AI on one saved record and describes the outcome in plain words.
export async function processCapture(sessionId: string, captureId: string) {
  try {
    const { capture } = await api<{ capture: Capture }>(`/sessions/${sessionId}/captures/${captureId}/process-ai`, "POST");
    const analysis = capture.analysis as WorkflowAnalysis | undefined;
    const filled = analysis?.filled_fields.length ?? 0;
    if (analysis?.failure === "provider") return `AI unavailable: ${analysis.warning} Labeled lines filled ${filled} field${filled === 1 ? "" : "s"}.`;
    if (analysis?.method !== "llm") return `AI answer rejected (${analysis?.warning}). Labeled lines filled ${filled} field${filled === 1 ? "" : "s"}.`;
    return `AI filled ${filled} field${filled === 1 ? "" : "s"}${analysis.rejected_fields?.length ? `; skipped ${analysis.rejected_fields.join(", ")} (not in the raw text)` : ""}. Review before approving.`;
  } catch (e) {
    return `AI processing failed: ${(e as Error).message}`;
  }
}

export type ContactBrief = { company_url: string | null; context: string; updated_at: string;
  research: { pages: string[]; facts: { fact: string; source_quote: string }[]; dropped_facts: number; fetched_at: string | null; model: string | null; ai_run_id?: string };
  brief: { hooks: string[]; credentials: string[]; bridges: string[]; asks: string[]; avoid: string[]; reference_draft: string } };
export type ContactLookup = { contact_key: string; found: boolean; about_me_set: boolean; brief: ContactBrief | null;
  contact: { person: string; company: string; fields: { label: string; value: string | number | boolean }[] };
  records: { capture_id: string; workflow_name: string; run_id: string; run_name: string; decision: string; action: Action; captured_at: string }[] };
export type PersonaPoint = { point: string; evidence: string };
export type Persona = { headline: string; summary: string; domains: string[]; strengths: PersonaPoint[]; proof_points: PersonaPoint[];
  dropped: number; stale: boolean; generated_at: string; model: string | null; ai_run_id?: string };
export type Profile = { about_me: string; resume_text: string; persona: Persona | null };
export const isProfileUrl = (url: string) => /^https:\/\/([a-z]{2,3}\.)?linkedin\.com\/in\/[^/?#]+|^https:\/\/(www\.)?(x|twitter)\.com\/[A-Za-z0-9_]+\/?(?:[?#]|$)/i.test(url);

export type AiKind = "capture_fields" | "brief" | "persona" | "source_analysis" | "recap_reflection";
export type AiStatus = "ok" | "partial" | "rejected" | "provider_error" | "fetch_error" | "error";
export const aiKindLabels: Record<AiKind, string> = { capture_fields: "Process with AI", brief: "Message brief", persona: "Persona",
  source_analysis: "Source analysis", recap_reflection: "Recap observations" };
export const aiStatusLabels: Record<AiStatus, string> = { ok: "OK", partial: "Partly grounded", rejected: "Rejected output",
  provider_error: "Provider error", fetch_error: "Research failed", error: "Error" };
export type AiRunSummary = { id: string; kind: AiKind; subject: string | null; status: AiStatus; model: string | null; prompt_sha256: string | null;
  meta: Record<string, unknown>; rejected_count: number; error: string | null; latency_ms: number | null; prompt_tokens: number | null;
  completion_tokens: number | null; rating: -1 | 1 | null; feedback: string; created_at: string };
export type AiRunDetail = AiRunSummary & { research: Record<string, unknown> | null; input: unknown; output: unknown; result: unknown; rejected: unknown[];
  prompt: { sha256: string; instruction: string; output_schema: unknown } | null };
export type AiVersion = { kind: AiKind; prompt_sha256: string | null; runs: number; statuses: Record<AiStatus, number>; avg_latency_ms: number | null;
  prompt_tokens: number | null; completion_tokens: number | null; thumbs_up: number; thumbs_down: number; first_at: string; last_at: string };

export type ActivityRun = { id: string; run_name: string; workflow_id: string; workflow_name: string; color: string; session_seconds: number; approved_records: number };
export type ActivityMonth = {
  month: string; today: string; timezone: "UTC"; date_basis: "run_started_at";
  days: { date: string; runs: ActivityRun[]; approved_records: number; session_seconds: number }[];
  workflows: { id: string; name: string; color: string }[];
  summary: { active_days: number; completed_runs: number; approved_records: number; session_seconds: number };
};
