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
- [x] Successful live OpenAI source analysis after replacing the rejected key (synthetic text).

## Parent workflows — active iteration
- [x] Preserve real records while grouping existing sessions under parent workflows.
- [x] Create/rename workflows and define typed fields with extraction instructions.
- [x] Dated, renameable runs with versioned field contracts.
- [x] Consolidated contact records with per-run/action/decision history.
- [x] One Raw capture text input; remove separate notes/source-analysis UI.
- [x] Generate downloadable DSL/prompt/JSON schema/JSONata; execute actual JSONata mapping.
- [x] Top Process with AI pass over saved pending records, fill empty fields only, preserve manual values.
- [x] Explicit connection-request action separate from initial messages; no inferred approvals.
- [ ] Use the updated workflow UI for the next real 40-record review.

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

### Rotated OpenAI key verification — 2026-11-10

User reported rotating the key. One bounded call to `analyze_source` with synthetic name/company/
role text returned `method: llm`, `model: gpt-4.1-mini`, `warning: null`. No personal contact or
LinkedIn text was sent. Verified and restarted only the project's local uvicorn process so cached
settings load the rotated key. Readiness returned `{"status":"ok","database":"ready"}`.
The prior key blocker is resolved for live source analysis; real-user review and live recap
observations remain the next usage experiment. This API success says nothing about LinkedIn
authorization: current manual-only behavior is not an approval or guarantee of account safety.

### Local PostgreSQL browser UI — 2026-11-10

User requested an easier local UI for inspecting project databases. Added Adminer as Compose
service `db-ui` (`adminer:5`), on loopback-only `127.0.0.1:8082`, with `db` as default server and
healthy DB dependency. PostgreSQL port/volume remain unchanged. Added optional `DB_UI_PORT` to
the example environment and documented login/table browsing/SQL/stop commands in README.

Checks: `docker compose up -d --wait db-ui` succeeded; Adminer HTTP 200 and authenticated login
using ignored `.env` credentials succeeded. Verified outreach_sessions, captures and session_recaps
appear in the table listing without printing credentials or row contents. `docker compose ps`
confirmed separate project DB/UI containers and loopback binding; `git diff --check` passed.
No schema changes, data mutations, unrelated container changes, application tests or commits.

## Workflow/run hierarchy and configurable extraction — 2026-11-10

User reported completing 40 contacts in about 24 minutes and requested parents for two repeated
activities, dated/renameable child runs, a consolidated contacts view, configurable fields, a
generated DSL + JSONata extraction system, and one top Process with AI button over pasted notes.

### Data preservation and migration

- Inspected existing session intentions/counts only: two founder intentions on Nov 9/10 and one
  outreach intention on Nov 9. Saved ignored `.local/pre-workflows.dump` before schema changes.
- Added migration `0003_workflows`: workflows + immutable workflow_versions, then backfilled existing
  sessions with owner-scoped workflow IDs, version and dated run names before NOT NULL/FK constraints.
  The two explicitly known founder titles group into **Fintech founder connections**; the known
  outreach title into **Contact outreach**. Other intentions keep their own group.
- Verified live grouping: founder runs 2026-11-09 (3 captures) and 2026-11-10 (40 captures, review),
  outreach run 2026-11-09 (1 capture). All 44 captures, decisions, raw/original data, session IDs and
  existing recaps preserved. No reset or retroactive action reclassification; backup remains private.

### Implemented

- Workflows page: create with founder/outreach template or minimal contact fields, add/remove/edit
  typed fields and instructions, rename parent, inspect dated runs, start run, download DSL/JSONata,
  and consolidated contacts. Editable run names and Run history preserve original intentions.
- Schema fields include Contact URL, Name, Company and configurable text/long text/number/boolean/
  date/URL fields. Founder defaults: role, location, industry, hiring signal. Outreach defaults:
  role, location, conversation context and explicit next step. Unknowns remain null; names are not
  treated as externally verified facts. Reserved activity/owner keys cannot become custom fields.
- Each version stores DSL fields, extraction system prompt, output JSON schema and trusted generated
  JSONata expression. `jsonata-python==0.7.1` runs the mapping after type/source-evidence validation.
  No arbitrary user expression execution. Fields evolution is explicit: existing runs retain their
  definition version; open runs can adopt additive updates, incompatible updates require a new run.
- Capture form/extension v0.4.0 now use **Contact URL + Raw capture text**; the old separate notes,
  page-title and source-analysis inputs are removed. Historical notes/quotes remain stored and are
  combined for processing only when needed. Original capture JSON is not overwritten.
- Top **Process with AI** traverses saved pending records sequentially; progress saved per record,
  stop-after-current, stops on navigation/fallback/error, and successful same-source/version results
  reused. Empty fields are filled automatically; manual non-empty fields, false and zero preserved.
  Each analysis stores workflow ID/version, raw hash, evidence, filled/preserved keys and actual
  provider/method. AI does not change action, approval, URL or follow-up date. No contacts are sent.
- Review supports Save draft changes before processing. Large runs use compact expandable cards
  with extracted-field chips. Approval remains explicit and existing duplicate checks still apply.
- Connection request sent (`connection_requested`) now differs from initial message sent; explicit
  person/action confirmation is required. Weekly request counts and recap actions stay distinct.
  Old “researched” actions are not inferred from profile “Pending” buttons or workflow names.
- Consolidation groups normalized profile URLs (fallback exact name/company or URL), fills latest
  non-empty logged values and links each dated run/action/decision. Pending entries labeled;
  discarded excluded. Current 5,000-record source limit is explicit, not silent truncation.
- README/PRODUCT_PLAN/AGENTS and docs/workflows.md updated. Prior source-analysis API/history kept
  compatible, but its removed UI is not the current workflow. New recaps include workflow/run/custom
  fields; historical completion snapshots stay unchanged.

### Checks

- `uv sync`: installed actual JSONata engine; `uv run alembic upgrade head && uv run alembic check`
  migrated development DB and reported no schema drift.
- `uv sync --frozen && uv run ruff check . && uv run pytest -q && uv run alembic check`: **49 real PostgreSQL tests passed**,
  lint/schema checks passed. Includes downgrade-to-prior-schema/data-preserving backfill, parent and
  linked-ID ownership, field version/sync behavior, actual JSONata evaluation, custom-field injection
  rejection, fill-empty/manual preservation, provider failure and concurrent edit, consolidation,
  and a synthetic 40-record processing pass without approval/action invention. Existing upstream
  Starlette/httpx deprecation warning remains.
- From apps/web, `npm exec --yes --package=node@22 -c 'npm run test:e2e && npm run typecheck && npm run lint'`:
  **5 browser tests passed**, TypeScript/ESLint passed. Real extension supports simplified raw capture;
  desktop/mobile cover creating fields, dated runs, local batch fallback, preserved manual values,
  rename, actual contract download, cross-run consolidated contacts, review/recap and no page overflow.
- Bounded live synthetic OpenAI workflow-contract request succeeded. Output passed grounded typed
  validation and genuine JSONata evaluation (person/company/role/location/industry). No real contact
  data was used, no user records processed automatically, and no full daily.dev/inbox integration.
- Inspected desktop/mobile workflow/consolidation and review screenshots in ignored test-results.
- Final `npm exec --yes --package=node@22 -c 'npm run typecheck && npm run lint && npm run build && node --check ../extension/popup.js && node --check ../extension/capture.js && node --check ../extension/background.js'` passed. Final browser rerun: **5 passed**.
- Verified live DB totals after migration: **2 workflows, 3 runs, 44 captures, 40 in review**.
  Restarted only the verified project uvicorn process to load current routes/settings. API readiness
  healthy and web HTTP 200. `git diff --check` passed. No commits/deployments or unrelated DB changes.

### Next experiment and limits

Reload extension **v0.4.0**; refresh app → Workflows → Fintech founder connections → Nov 10 run →
Process with AI. Review the filled fields; existing manual values remain. The implementation has
not spent 40 real provider calls on the user's records—processing starts only on their button click.
Use Edit fields & name to add missing fields, then explicitly sync the open run if needed.

Current processing is a resumable foreground UI loop, not a server-side scheduled worker. One open
run per account remains. Completed/approved records are not silently enriched; historical amendment
needs a separate reviewed design. Identity consolidation is deterministic, not fuzzy verification.
Only the latest per-record AI result is stored, alongside immutable original data and versioned DSL.

## Same-day repeat runs and manual-value preservation — 2026-11-11

User asked to inspect the DB, ensure AI never overwrites manually filled records, and allow
multiple sessions of a workflow in a day with optional names or date + numbered defaults.

### Inspection

- Read-only project DB checks found **2 workflows, 3 runs, 44 captures, 40 pending**. Only one
  capture had workflow-analysis schema v2. That result had method `local`, warning
  `AI field is not supported by the raw text`, and empty filled/preserved lists. Its original
  name and company were both empty and unchanged. No record was processed or renamed during
  inspection; the stored attempt rejected unsupported facts rather than silently filling them.
- Code inspection confirmed the server already merges into freshly reloaded details after the
  provider call and only fills null/empty fields. Added targeted tests rather than weakening
  evidence validation. Original-data comparisons alone cannot attribute later edits to AI.

### Changes

- `run_names.py` generates per-workflow UTC-day names: date, date (1), date (2), etc. All same-day
  sessions count, including custom/renamed runs; explicit occupied suffixes are skipped. A new UTC
  day or different workflow has an independent sequence. Creation assigns one consistent server
  timestamp and allocates under the existing owner lock. No migration or existing-name rewrite.
- Blank/whitespace run names now mean automatic naming. The start form still accepts a custom
  name and shows the server's next-name preview, with repeat-run/UTC guidance. The existing one-open-
  run rule remains: finish/review/complete the current run, then start another on the same day.
- Process with AI is disabled while capture forms contain unsaved edits. Editable fields are
  locked during a processing pass, and Finish & review waits for edits to be saved/cancelled.
  Removed AI-source-hash form remounting: clean forms refresh on changed stored details, while
  polling does not replace an unsaved draft. A same-source fallback retry can now refresh fields.
- Tests explicitly verify saved names/company/custom text, `0`, `false`, concurrent manual saves
  during provider latency, manual corrections after processing, cached reruns and changed-source
  reruns. None are overwritten by AI; only empty fields are filled and originals remain intact.

### Verification

- `uv run ruff check . && uv run pytest -q services/api/tests/test_workflows.py services/api/tests/test_sessions.py`:
  **31 focused PostgreSQL tests passed**, lint passed.
- `uv run ruff check . && uv run pytest -q && uv run alembic check`: **52 tests passed**, no schema
  drift. Existing upstream Starlette/httpx deprecation warning remains.
- From apps/web, `npm exec --yes --package=node@22 -c 'npm run typecheck && npm run lint'`: passed.
- From apps/web, `npm exec --yes --package=node@22 -c 'npm run test:e2e && npm run build'`:
  **6 browser tests passed**, production build passed. Added four sequential same-day runs with
  defaults/custom names, and desktop/mobile unsaved-edit blocking + in-flight input-lock checks.
- Tests used disposable DB data and synthetic provider output; no live LLM calls or user records
  changed for testing. Next experiment: save any manual corrections, rerun processing, then complete
  the current review and start a second named/default run. Existing 40-record review remains intact.
- Final read-only live DB check still showed **2 workflows, 3 runs, 44 captures, 40 pending, one
  workflow-processed record**. Restarted only the verified project's API process to load the new
  naming behavior. API readiness healthy, web HTTP 200, and `git diff --check` passed. No migration,
  existing-name rewrite, commit, deployment, or unrelated database changes.

## Process with AI stuck on the first record — 2026-11-11

User reported the AI button "not working". The API log showed clicks did reach
`process-ai` and return 200. The first pending record's model answer was rejected wholesale
(`AI field is not supported by the raw text`) because one field failed exact-substring grounding,
the record fell back to `local`, and the UI stopped the whole pass on any non-LLM result. Each click
therefore retried, and paid for, the same first record and never progressed.

### Changes

- `ground_output` in `workflow_contracts.py` checks evidence per field. It drops only
  unsupported/invalid values and returns them as `rejected_fields`. Matching normalizes
  whitespace, case, NFKC and smart quotes/dashes, never wording. Unknown/system fields or missing
  evidence still reject the whole answer. `transform_output` remains strict for callers that need it.
- `process_capture` separates `failure: "provider"` from `failure: "output"`. A partially grounded
  answer stays `method: "llm"` (cached as before), with a warning naming skipped fields. Labeled
  local `Field: value` lines fill fields the model omitted or got rejected for. The fill-empty-only
  merge, original data and manual-value preservation are unchanged. No migration; analysis JSON
  gained two keys.
- `run-ai.tsx` stops only on provider failure and counts flagged records in the final status.

### Verification

- `uv run ruff check . && uv run pytest -q && uv run alembic check`: **54 passed**, no drift. Added
  partial-grounding/normalization/caching and provider-vs-output failure tests. Moved the concurrent
  edit check to a fresh record because a partial LLM result is now cached.
- From apps/web: typecheck, lint, and `npm run test:e2e`: **7 browser tests passed**, including new
  `ai-pass.spec.ts` (flagged records continue; provider failure stops at the third record).
- Read-only live dry run on the previously failed record (one real provider call, no DB write):
  the model returned person/location/role. Old code discarded all three; now person and location are
  kept, and role (not literally in the text) is skipped.
- Live DB unchanged: **2 workflows, 3 runs, 44 captures, 40 pending, 1 workflow-processed**.
  Restarted only the project API on :8000; readiness healthy.
- Next experiment: click Process with AI on the 40-record review. Check how many fields were
  skipped per record. If `role`/`hiring_signal` are often skipped, adjust their instructions
  to ask for verbatim phrases.

## Reused pasted text + bulk approve — 2026-11-11

User spotted "anchal Kokkuvayil" twice and asked for other repeats plus a bulk approve button.

### Inspection (read-only)

- The two Anchal records share identical raw text but have different URLs (`/in/chanchalkg`,
  `/in/ossareh`), saved 20s apart: the second profile was saved with the previous clipboard.
- Same pattern in **4 pairs**, all pending in run 2026-11-10: Anchal Kokkuvayil
  (chanchalkg / ossareh), Maria Cannizzo (mariacannizzo / chaz-guinn-25695b35), Sudhakar
  Kondisetty (sksgsc / sanjibkalita), Winston Damarillo (wdamarillo / vincemolinari). The first
  URL in each pair matches the name; the second profile's own text was never captured.
- Carolina Di Renzo same-URL pair (2026-11-09) was already resolved: one approved, one discarded.
- No records were changed; the user decides which to re-paste or discard.

### Changes

- `session_view` adds `same_raw_text_as`, and the review card shows a stale-clipboard notice.
- `POST /sessions/{id}/captures/bulk-approve` plus a two-step **Approve all eligible (N)** button.
  It skips confirmed actions, duplicates, reused-text records and already-approved contacts.
  `confirmedActions` is shared in `lib/api.ts`. No migration.

### Verification

- `uv run ruff check . && uv run pytest -q`: **55 passed** (new flag/bulk test incl. ownership,
  wrong state, skip reasons, late records untouched, idempotent re-run).
- From apps/web: typecheck, lint, `npm run test:e2e`: **8 passed** (new `bulk-approve.spec.ts`).
- Read-only check on the live 2026-11-10 run: 40 pending, 8 flagged (the 4 pairs), 0 duplicates,
  0 needing confirmation, **32 bulk-eligible**. Restarted only the project API; healthy.
- Next experiment: fix or discard the 4 flagged second records, run Process with AI, spot-check
  fields, then Approve all eligible and approve the corrected ones individually.

## Review filters, card counts, consolidated manual entry — 2026-11-11

User asked for Waiting for review / Approved filters with totals visible on cards before
opening, and manual entry with the AI button in the consolidated view.

### Changes

- `workflow_view` adds workflow `pending_count` and per-run `pending_count`/`approved_count`.
  No migration.
- Workflow cards show Total records / Waiting for review / Approved. Run rows show waiting and
  approved counts.
- Shared `FilterChips` (All / Waiting for review / Approved [/ Discarded]) with counts. Used for
  dated runs, consolidated contacts and a run's records.
- `WorkflowEntry` in consolidated records reuses `CaptureForm` and `RunAI`. It targets this workflow's
  open active run (Resume if paused; explicit start if none). It doesn't bypass a run in review or
  another workflow's open run.

### Verification

- `uv run ruff check . && uv run pytest -q`: **55 passed** (count assertions added).
- From apps/web: typecheck, lint, `npm run test:e2e`: **9 passed**, including new
  `workflow-filters.spec.ts` (start run from consolidated view, two manual records, AI provider error
  keeps local fill, chips/counts on contacts, runs, records, card).
- Live read-only state: run 2026-11-10 is in review with **36 approved, 1 waiting, 3 discarded**.
  Earlier runs are completed. Until that review is completed, consolidated manual entry shows
  "in review" with an Open review button. Restarted only the project API; healthy.
- Next experiment: finish the last pending record, complete 2026-11-10, then add a record from
  consolidated view and process it with AI.

### Follow-up: Process with AI disabled on a new manual record

User filled the consolidated-view form and found Process with AI disabled. This was expected:
the record was unsaved (dirty form) and the run had 0 saved pending raw-text records. Two clicks
were needed (Capture for review, then Process with AI), which was not obvious. Added a
**Capture & process with AI** submit button to every new-record form. It keeps browser validation,
requires raw text, saves, then calls `process-ai` for that record only and reports the outcome
inline: AI filled / skipped fields, provider unavailable, or rejected answer. The disabled-state hint
now points to it. No API change. Verification: typecheck, lint, **9 browser tests passed**; the
filters spec covers the validation block, then a one-step capture + local fill without a provider key.
