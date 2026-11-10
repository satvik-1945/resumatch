# Outreach sessions — new product baseline

Status: user-approved reset and first vertical slice. Resumatch is a working repository name.

## Purpose
Make Satvik's job-search outreach easy to record and rewarding to sustain. Discover interesting
fintech/startup/AI companies, research people, reach out through existing channels, and learn
from an honest history. The inspiration is Strava's activity loop, not its entire feature list.

## First loop
Start an outreach session with an intention → browse normally → explicitly capture page context
and action → finish/pause → review captured records → approve or discard → see session progress.
No resume/profile onboarding. No required paid provider or LLM.

## Parent workflows and dated runs — refinement from real usage
Satvik reported 40 contacts in about 24 minutes and repeated a fintech-founder activity across
two days. A workflow now owns its field definitions and each session is a dated, renameable run.
Initial parents: Fintech founder connections and Contact outreach. Consolidated records group
contacts across runs without deleting their per-run history or counting pending actions as approved.

Create workflow → choose/add fields → start a dated run → capture Contact URL + Raw capture text →
Process with AI at the top → review filled fields and explicit actions → approve → recap.
The earlier separate notes/source-text panels are replaced by one Raw capture text input.
Each workflow compiles a versioned DSL, prompt, JSON schema and trusted generated JSONata mapping.
AI fills empty fields only, keeps unknowns empty, and never decides what action happened.
Definitions can evolve; existing runs adopt additive changes explicitly. Keep all real records.

First channel assumption: desktop LinkedIn, based on prior user behavior. Capture also works on
company/news pages; sending still happens in the real channel. Confirm the preferred channel
through actual usage rather than blocking a generic browser-capture experiment.

## First release
- Real local accounts and private data.
- One open session per account, durable start/pause/resume/finish/review/completion.
- Timer is explicitly session time. Pause on request; never pretend it proves attention.
- Browser extension with explicit active-tab permission; editable page title/URL/selected text.
- LinkedIn is manual logging only: no LinkedIn DOM/title/selection reading or HTML overlays.
  This is a reduced-integration design, not a claim of LinkedIn approval; see the terms research.
- Browser-owned movable capture window; explicit opening, collapse/hide, optional hide after save.
- One record per identified person per session, with edit-existing guidance and legacy duplicate review.
- Fast manual capture fallback. Action choices: researched, drafted, sent, followed up, replied.
- Captures are durable drafts. Review edits, rejects or confirms them; only approved actions count.
- History, a simple weekly session target, honest approved-action totals, and due follow-ups.
- Browser authorization gives capture-only access, not account-history or approval access.
- Workflow-level **Process with AI** fills configured fields from saved raw text, with evidence
  and visible progress/fallback. Processing and approval remain separate; no inferred actions.
- Completed-session JSON snapshots and recap cards compute counts from approved records. Optional
  AI observations cite approved source excerpts and never change metrics or fabricate success.

## Later, after five real sessions
- Daily discovery from daily.dev and primary company/investor sources.
- A local MCP adapter to the same capture API, exposing proposal tools rather than auto-approval.
- Authorized provider signals for actual sends/replies; validate access per channel.
- Sourced person/company relationships, maps of known locations, account-controlled share cards.
- Pseudonymous community presence, optional real-name reveal, accountability groups.
- User-chosen consistency goals and descriptive trends. No fabricated offer predictions.

## Definitions
Research is not contact. A draft is not a send. A clicked Send button is not guaranteed delivery.
An approved manual action is user-confirmed, not independently platform-verified.
Company headquarters is not the contact's location. Funding is not proof of hiring.
Replies and effort are reported separately. Goal completion must never publish identity.

## Scope discipline
Acceptance is five real sessions with capture taking seconds and review roughly a minute.
First make the logger useful. Add discovery, social features and monetization only after this
loop works. Candidate source daily.dev has official MCP/API docs; authenticated access remains
unverified without user authorization. See docs/daily-dev-research.md.

## Reset
The previous resume/profile/persona/evidence app and database tables were explicitly rejected.
Archive its planning documents only. Preserve .git and local secrets. Reset only resumatch and
resumatch_test in the dedicated resumatch-db-1 container; other projects are out of scope.
