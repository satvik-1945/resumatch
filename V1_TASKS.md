# Outreach sessions — build checklist and handoff

This is the active checklist. Earlier resume-first work is superseded in docs/archive/.

## First usable experiment
- [x] Project source/database reset and new baseline documented.
- [x] Local accounts, server-validated identity and ownership.
- [x] Durable session start, pause, resume, finish, review and completion.
- [x] Fast manual capture with honest action types.
- [x] Browser-assisted capture using explicitly authorized current-tab context.
- [x] Capture-only extension credentials, revocation and idempotent retry.
- [x] Review/edit/approve/discard; unreviewed records do not count.
- [x] History, weekly session target and due follow-ups.
- [x] Two-user API and actual browser-extension checks.
- [x] Document setup, extension pairing and verification commands.
- [ ] Run five real sessions with Satvik.

## daily.dev
- [x] Verify official MCP/API documentation and access requirements.
- [ ] User supplies daily.dev authorization; bounded read-only live check.
- [ ] Measure source relevance before adding daily scheduled discovery.

## Review intelligence and session recap
- [x] Explicit source-text analysis with editable, source-backed suggestions and local fallback.
- [x] Store analysis separately from reviewed records; never infer sent/reply actions.
- [x] Completed-session recap snapshot, visible progress card and downloadable JSON.
- [x] Optional bounded source-linked observations from approved records only.
- [x] Fix intrinsic popup sizing; responsive movable window without obscuring controls.
- [ ] Successful live OpenAI analysis after replacing the rejected key.

## Current handoff
## Implemented first slice

The session → capture → review → history loop is implemented. The old resume-first app code,
migration chain, uploads and both project DB public schemas were reset under explicit user
authorization. Only historical planning documents were archived. Local secrets and Git history
were preserved. No other project databases or containers were changed.

New schema head: `0001_outreach`. Tables: users, logins, outreach_sessions, session_events,
captures, extension_pairings, plus alembic_version. The dedicated container remains on 55432.

Web: Next.js/TypeScript private accounts, Today, start/pause/resume/finish/complete, manual
capture, editable review, history, weekly target and due reminders. Weekly boundaries use UTC.
Only approved records count; sessions need at least one approved record to count toward goals.

Chrome MV3 extension: explicit activeTab capture of URL/title/selected text, editable person,
company/action/channel, local unsent draft, idempotent request retries. Pairing tokens are
hashed server-side, capture-only, tied to an extension ID, expire in seven days and revocable.
Real Chrome privileged GET requests may omit Origin: bearer token plus X-Extension-ID is
required, and any supplied Origin must match. This is a narrow bearer capability, not proof
of a particular client executable. See docs/outreach-architecture.md.

## Verification — first slice

- `uv sync --frozen && uv run ruff check . && uv run pytest -q && uv run alembic check`:
  dependency lock, Python lint and schema checks passed; **17 real PostgreSQL tests passed**.
  Includes concurrent starts, transition/timer persistence, ownership, review/action confirmation,
  retry deduplication, pairing scopes/revocation/expiry and privileged GET origin behavior.
  One upstream Starlette/httpx deprecation warning remains.
- From `apps/web`, `npm exec --yes --package=node@22 -c 'npm run typecheck && npm run lint && npm run build && node --check ../extension/popup.js && node --check ../extension/capture.js && node --check ../extension/background.js'`:
  TypeScript, ESLint, production build and extension JavaScript syntax checks passed.
- From `apps/web`, `npm exec --yes --package=node@22 -c 'npm run test:e2e'`:
  **3 browser tests passed**. Desktop 1440px and mobile 390px flows cover session refresh,
  pause/resume, manual capture, explicit sent confirmation, review completion and history.
  The actual unpacked extension was loaded into persistent Chromium, paired with the real API,
  captured selected text from a controlled loopback page, saved/reviewed/completed and revoked.
  That test is not evidence of LinkedIn inbox access or a live daily.dev feed connection.
- Reviewed desktop review/mobile history screenshots in ignored apps/web/test-results.
  `git diff --check` passed. No commits, deployment or purchases.
- On continuation, `uv run alembic upgrade head && uv run alembic check && git diff --check`
  passed. Started local API on 8000 and web dev server on 3000; readiness returned
  `{"status":"ok","database":"ready"}` and web returned HTTP 200. Logs are ignored
  `.local/api.log` and `.local/web.log`. App is available at http://localhost:3000.

## daily.dev finding and quota check

Official docs confirm remote MCP at https://api.daily.dev/mcp and public API support, currently
beta. OAuth or a daily.dev token is required. Personalized feeds/search/post details are useful
research sources, not verified funding/contact facts. Current public pages have inconsistent
quota wording; effective account limits must be checked with authenticated response headers.

No daily.dev token or OAuth access is configured. On the user's request to check API reset,
configuration presence was checked without exposing secrets: daily.dev token absent; local
LLM key present but endpoint/model absent. No account quota/reset time could be verified.
Coding-agent provider quota is not exposed by repository tools; successful tool calls do not
prove a particular limit-reset time. No unrelated LLM key was sent to daily.dev.

## Next experiment

Create a new local account and install apps/extension as an unpacked extension. Do one real
15-minute LinkedIn/company-news session with 3–5 explicit captures, review and complete it.
Record capture time, review time, missed/duplicate captures, corrected person/company/action
fields, and whether returning for another session feels useful. Repeat five times before adding
discovery automation or public features. Test real toolbar activeTab grants on the chosen sites;
the controlled-page test cannot establish all live site behaviors.

No provider authorization has been supplied. daily.dev integration remains a separately bounded
read-only live experiment once the user authorizes their own account. See docs/daily-dev-research.md.

## LinkedIn terms, capture-window usability and duplicate follow-up — 2026-11-09

User tested real captures and requested official-source terms research, a movable/collapsible
capture UI, a tour of follow-up dates, and prevention of repeated people within a session.

### Research and decisions

- Fetched LinkedIn's current User Agreement and official Prohibited software and extensions help
  page. The agreement says effective November 3, 2025. Sections 8.2.2/4 restrict scraping/copying,
  8.2.13 unauthorized automation, 8.2.15 overlays; 3.4 describes account restrictions/termination.
  Lack of HTML modification did not establish permission for the previous text-reader.
- LinkedIn now dispatches to manual logging: user-selected browser URL only; no LinkedIn DOM,
  title, selection or inbox reads. A defensive page-reader guard also rejects LinkedIn before
  DOM access. No claim that this guarantees contractual compliance or legal/account safety.
- Verified Chrome windows/sidePanel documentation. A separate browser-owned movable window meets
  free positioning without an in-page overlay. SidePanel stays a possible docked alternative.
  Details/sources: docs/linkedin-capture-review.md; updated AGENTS/plan/README accordingly.

### Implemented

- Extension v0.2.0: **Open movable window**, starts near the source window's left side; native
  drag/resize; Collapse/Expand and Hide controls; optional hide/minimize after successful save.
  Native resize bounds are clamped to the display work area and UI state changes only after a
  successful resize. No background navigation listeners or unsolicited auto-popups. Reload the
  unpacked extension to activate changes. The toolbar popup remains available.
- Source title/text moved to optional collapsed details; sticky capture action. Existing draft
  edits survive. LinkedIn manual-mode notice distinguishes URL metadata from page-content reads.
- `duplicates.py`: session-local canonical LinkedIn/X profile matching, normalized known-name
  checks and identical anonymous-source checks. Different explicit identities beat equal names;
  different known people on a shared source are not merged. This is not fuzzy identity resolution.
- New captures check subject duplicates under the existing session lock, including concurrent
  distinct request IDs; 409 identifies the existing record. Retry-idempotency remains intact.
- Authenticated **Edit capture** updates pending records while active/paused (preserves original).
  Update the existing action/notes/reminder instead of recapturing the person. No automatic merges
  or deletion of the user's existing records. Legacy duplicates are flagged and cannot both be
  approved; discard extras during review. Same people are allowed in later sessions.
- Cards now show company, activity time, and follow-up date or explicit absence. Pending dates say
  planned/awaiting approval. Approved future reminders appear under **Upcoming follow-ups**;
  dates due by UTC day appear under **Due follow-ups**. Clearing doesn't record a send.
- No schema changes or migration reset. Live local API was restarted with these code changes;
  existing accounts/session/capture records preserved. Readiness healthy and web HTTP 200.

### Checks and exact results

- `uv run ruff check . && uv run pytest -q`: **24 real PostgreSQL tests passed**, lint passed.
  Added profile-URL variants, name/channel matching, concurrent duplicates, edit/original safety,
  future reminders and isolation, legacy duplicate review, and subsequent-session reuse.
- From apps/web, `npm exec --yes --package=node@22 -c 'npm run test:e2e && npm run typecheck && npm run lint && npm run build && node --check ../extension/popup.js && node --check ../extension/background.js && node --check ../extension/capture.js'`:
  **3 browser tests passed**, TypeScript/ESLint/production build and JS syntax passed. Desktop/mobile
  cover duplicate rejection, edit-existing, follow-up visibility through review and history.
- Follow-up native-window bounds correction verified by
  `npm exec --yes --package=node@22 -c 'npm run test:e2e -- extension.spec.ts'`: **1 passed**.
  Actual extension window opened, collapsed/expanded with no errors, auto-minimized after save,
  rejected a duplicate, and completed the reviewed reminder flow. Screenshot inspected in ignored
  test-results/*/movable-capture.png. TypeScript/ESLint also passed after hide-after-save coverage.
- Packaged LinkedIn dispatch tested with synthetic tab metadata and a reader that must not run;
  zero content reads. No LinkedIn account/page scrape occurred in tests, and no platform approval
  is implied. Native title-bar dragging is OS-provided, not simulated as a DOM overlay.
- `uv run alembic check`, `git diff --check`: passed, no schema drift. Existing Starlette/httpx
  deprecation warning remains. No commits, deployment, purchases or delegation.

Next: reload extension v0.2.0, refresh the app, finish the current real session, discard previously
captured duplicates and verify the planned reminder appears after approval. Then measure capture/
review time in five real sessions. A screenshot of a profile does not verify company affiliation,
and deterministic matching cannot resolve unknown identities or every spelling variant.

## Source analysis, JSON recaps and popup fix — 2026-11-10

User requested terminal commands for inspecting tables, renewed LinkedIn compatibility guidance,
an explicit review-tab LLM pass to suggest names/context, structured session conclusions, and a
fix for the screenshot's extremely narrow toolbar popup. They subsequently asked to finish the
last integration/verification step.

### Implemented

- Extension v0.3.0: explicit 420px HTML/body width for toolbar popups, removing the self-referential
  max-width:100vw constraint that allowed intrinsic shrinkage. Separate responsive root/body rules
  for movable windows, improved labels/spacing, optional source details and non-overlapping save
  button in normal document flow. LinkedIn remains manual-only; no new page-reading behavior.
- `captures.analysis` JSONB stores schema-v1 source proposals: exact input/hash, method/model,
  timestamp, name/company/role/key points with verbatim source quotes, and fallback warning.
  **Analyze source text** only on pending captures in review; using suggestions edits the form,
  not the DB approval/action. Changed source invalidates suggestion use until reanalysis.
- Server validates exact source support, disallows unknown/action fields, checks ownership/origin
  and rechecks state after provider latency without holding DB locks. Current approved stats and
  record decisions remain unchanged by analysis. Local fallback only handles labeled fields.
- Added `session_recaps` and migration `0002_analysis_recaps` (new head). At completion, transactional
  schema-v1 payload stores intention/time, counts by approved action/channel, known logged identities,
  discarded/unknown counts, highlights, limitations, approved activities and follow-up snapshot.
  Older completed sessions get a recap lazily. No data reset; existing captures/accounts preserved.
- New recap card with activity bars, next steps, history access and **Download session JSON**.
  Counts/highlights come from server calculations, not the model. Snapshot dates remain distinct
  from Today reminder-clearing status. Seven domain tables now, plus alembic_version.
- Optional **Find AI observations** extracts/cites supported approved-source snippets. Bounded to
  20 populated records / 16,000 characters, plus output/time limits. Stored separately as reflection;
  invalid or unavailable output leaves computed recap intact. No pending/discarded source content.
- User confirmed OpenAI; configured ignored `.env` with https://api.openai.com/v1 and configurable
  gpt-4.1-mini while preserving key. One bounded live call used synthetic text only. Provider
  rejected credentials/access; method correctly returned local with an explicit warning. **No
  successful live LLM response verified.** User must replace the key in ignored `.env` and restart.
  `.env.example` contains placeholders only. Tests disable real keys and use mock transports.
- README and docs/source-analysis-and-recaps.md document schemas, table inspection, provider setup,
  privacy/review boundaries and failures. Pasted LinkedIn text is not a terms-compliance exemption.

### Final verification

- `uv sync --frozen && uv run ruff check . && uv run pytest -q && uv run alembic check`:
  **37 real PostgreSQL/API tests passed**, lint and schema drift checks passed. Covers private proposal
  persistence, no auto-overwrite/actions, concurrent state change, fabricated/malformed provider
  output, prompt-instruction/action-field rejection, auth/quota fallback, snapshot stability,
  discarded-source exclusion, ownership, bounded observations and lazy historical recaps.
  Existing upstream Starlette/httpx deprecation warning remains.
- From apps/web, `npm exec --yes --package=node@22 -c 'npm run test:e2e && npm run typecheck && npm run lint && npm run build && node --check ../extension/popup.js'`:
  **3 browser tests passed**, TypeScript/ESLint/production build and JS syntax passed. Browser tests
  cover local suggestions, explicit use/edit/approval, unchanged actions, rendered recap, JSON
  download, missing-provider observations fallback, history and desktop/mobile flows. Real extension
  tests assert intrinsic root/body 420px width, pairing, movable-window behavior, capture/dedup and
  revocation. AI browser flows use local fallback, not a fake claim of real OpenAI success.
- Inspected desktop/mobile recap screenshots and unpaired extension screenshot in ignored
  apps/web/test-results. Migration upgrade/head drift check passed on development DB.
- Restarted only the verified project's uvicorn API process to load the new routes/settings.
  Readiness returned `{"status":"ok","database":"ready"}` and web HTTP 200. `\dt` confirmed
  session_recaps alongside existing project tables. `git diff --check` passed. No commits/deployments.

Next: replace rejected OpenAI key, restart API, reload extension v0.3.0, refresh app and run an
actual review → analysis → explicit field use → approval → recap flow. Metrics/JSON/local logging
are already usable. Continue five real sessions before expanding discovery or sharing.
