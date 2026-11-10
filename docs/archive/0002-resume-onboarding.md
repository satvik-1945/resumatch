# ADR 0002: Guided onboarding and reviewed resume imports

Status: superseded by the outreach-session reset; historical reference only.

## Product flow

The profile-only preview was a dead end. The authenticated workspace now has real navigation:
overview, resume import, profile, search personas, and proof of work. A visible setup sequence
connects import → profile review → persona selection → workspace. Saving a profile can advance
directly to persona selection. Existing accounts enter the overview with next actions based on
their actual saved profile, personas, and evidence.

Dropdowns offer common availability, notice, timezone, relocation and currency choices. Custom
values preserve previously entered preferences. Unknown remains a valid selection. Location is
not work authorization; timezone choice is not proof of mandatory timezone compatibility.

## Import pipeline and review boundary

- Accept UTF-8 TXT, text-based PDF, or pasted text. File limit: 5 MB. PDF limit: 20 pages.
  Text limit: 60,000 characters. Malformed, encrypted and scanned PDFs give paste-text guidance.
- Extract text server-side with pypdf. Store raw upload bytes in private local storage, using
  opaque UUID keys, restrictive permissions and SHA-256 hashes. Only the authenticated owner's
  download endpoint exposes files. Files are not served as static assets.
- Store a durable `resume_imports` proposal with source text, attributed field suggestions,
  evidence suggestions, extraction method and warnings. Extraction never edits the profile.
- Recent imports allow users to reopen a pending review after refresh. Summary lists omit source
  text; details and downloads are owner-scoped. Applied imports remain inspectable.
- The review UI selects only suggestions for blank profile fields by default. Replacing existing
  values is explicit. Suggested values can be edited; evidence is selected separately.
- Apply checks the authenticated owner and profile version, and locks the proposal. Profile update,
  selected evidence creation and import state transition share one transaction. Reapplying an
  applied proposal does not duplicate evidence. Original proposal and reviewed details are stored
  separately to preserve provenance.

## Extraction providers

Local extraction works without credentials and preserves verbatim source spans. It recognizes
introductory names/headlines, multiline summaries, exact stated experience, and common resume
sections. Approximate experience (e.g. “nearly 2.5 years”) stays in prose rather than silently
becoming an exact number. Location, salary and work authorization are not inferred from a phone
number or employer. Layouts still require user review.

An optional OpenAI-compatible chat-completions adapter uses server-only `LLM_API_KEY`,
`LLM_BASE_URL` and `LLM_MODEL`. All three must be supplied; a key alone never chooses a provider.
The user clarified that Astra refers to the coding model, not the resume extraction model.

Provider requests have bounded timeouts and response sizes, no automatic redirects, and explicit
instructions treating resume text as untrusted data. Provider proposals are schema-validated and
must be extractive with quotes found in the source. Unsupported output or provider failures fall
back to local extraction with a visible warning. Candidate-submitted claims remain candidate
claims, not externally verified achievements. No actual live provider integration is claimed.

## Search personas and evidence

`candidate_evidence` and `search_personas` are private records. APIs validate writes, enforce
owners on detail/update/delete, and paginate lists. Personas have configuration version counters
and three editable role templates with no fabricated skills or seniority. Arrangement selections
are search preferences, not eligibility assessments. Historical match-input snapshots are deferred
until matching is implemented.

This slice does not implement opportunity capture, application/outreach tracking, ranking or
document generation. These remain explicitly tracked in V1_TASKS.md.

## Storage and operational limits

`RESUME_STORAGE_PATH` defaults to ignored `.local/resumes`; backups must include both PostgreSQL
and this directory to restore original files. S3 storage, OCR, retention/deletion of original
imports and public-deployment upload limits remain future operations work. Do not commit real
resumes, keys, or local upload directories. Tests use synthetic content and a separate test DB;
browser tests disable external LLM calls.
