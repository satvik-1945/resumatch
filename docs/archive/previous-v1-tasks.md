# Superseded resume-workspace checklist — historical reference only

Read `PRODUCT_PLAN.md` and `AGENTS.md` before implementation.

## V1 definition

A working personal-search product with multiple personas, durable logging, manual hiring-post capture, narrow automated company-board discovery, explainable eligibility/ranking, evidence-grounded documents/outreach, follow-ups, and a grounded coach. Architecture and access boundaries must support additional users, verified with at least two test identities.

The first usable release is milestone 1. Continue through the remaining milestones to complete V1; do not substitute a UI mockup for working persistence or integrations.

## 0. Foundation

- [x] Inspect repository state and record the implementation approach.
- [x] Scaffold web, API, and local PostgreSQL with reproducible setup.
- [x] Choose and document authentication/session validation, migration tooling, durable queue, and storage adapters.
- [x] Add example environment configuration, health checks, and relevant lint/type/test commands.
- [x] Add initial migrations and server-enforced ownership patterns.
- [x] Document local start, migration, seed, and test commands in README.

Acceptance:

- [x] A fresh checkout can run documented setup and start web/API/database.
- [x] Migrations run from an empty database and configuration errors are actionable.
- [x] A real authenticated request resolves the server-validated identity; private routes reject unauthenticated requests.
- [x] Two-user access tests establish isolation for the initial private models.

## 1. Search workspace — first usable slice

- [x] Profile editor with optional experience, location, compensation, notice, timezone, and work-authorization fields.
- [x] Candidate evidence CRUD with supporting URLs/text.
- [x] Multiple editable personas; offer the three agreed role templates without inventing skill/level details.
- [ ] Company/contact records and affiliations.
- [ ] Manual role, company lead, and LinkedIn hiring-signal capture from URL plus pasted text.
- [ ] Editable structured fields and preserved source attribution; extraction must have a manual fallback.
- [ ] Opportunity detail with contacts, evidence, notes, and next action.
- [ ] Durable applications, stages, and transactional event history.
- [ ] Separate manually tracked outreach threads/messages.
- [ ] Follow-up tasks with due dates and completion.
- [ ] Dashboard showing active pipeline and due actions, plus useful empty/error states.

Acceptance:

- [ ] Capture a hiring post, associate company/contact/evidence, create outreach and a task, and log an application.
- [ ] Records survive refresh and process restart; changing application stage preserves history.
- [ ] Drafting/opening links does not mark messages sent or applications submitted.
- [ ] Another user cannot read, edit, link to, or infer private records through lists/detail/search endpoints.
- [ ] Manual capture and tracking require no scraper or LLM credentials.

## 2. Discovery and source operations

- [ ] Company watchlist and configured board/site identifiers.
- [ ] Greenhouse public listing connector.
- [ ] Lever public listing connector, including pagination and region/base-URL configuration where needed.
- [ ] Recruiter directory seeded with Hirojet, ClanX, Turing, EliteBrains as editable research targets, without fabricated contacts or integrations.
- [ ] Saved LinkedIn searches preserving the exact founder query and original URL from the product plan.
- [ ] Role-specific query variants; manually verifiable Posts-filtered search support.
- [ ] Source item normalization, native IDs, canonical URLs, content hashes, and provenance links.
- [ ] Conservative deduplication and idempotent upserts.
- [ ] Durable collection tasks, scheduler, retries/backoff, per-source timeouts/rate limits.
- [ ] Ingestion run counts/errors, last success, freshness, and stale/closed handling.

Acceptance:

- [ ] Fixture-based connector tests verify field mapping, pagination, timestamps, and errors.
- [ ] Repeated ingestion does not duplicate listings and preserves private application data.
- [ ] A failing source does not discard other source results; failure is visible and retry is bounded.
- [ ] Absence from an incomplete/failed fetch does not incorrectly close a job.
- [ ] Optional bounded live smoke checks are documented distinctly from fixture tests.
- [ ] Unknown publication date is not replaced with fetch time or displayed as a fresh post.

## 3. Eligibility and personalized feed

- [ ] Arrangement-specific eligibility assessments with evidence and `eligible`/`ineligible`/`unknown`.
- [ ] Country, mandatory timezone, work authorization, contracting, and relocation constraints.
- [ ] Explainable initial scorer with component scores and versioned persona/scorer inputs.
- [ ] Role, hiring-signal, and company-lead cards.
- [ ] Qualified feed and explicit unknown/research lane.
- [ ] Save, dismiss with reason, seen state, and feedback per user.
- [ ] Freshness/open-state indicators, next action, relevant contacts, and evidence links.

Acceptance:

- [ ] US-only remote listing is not labeled eligible for India-remote employment.
- [ ] An unspecified remote geography remains unknown; contracting eligibility is not inferred from employee eligibility.
- [ ] Explicitly supported arrangements can qualify even when another arrangement is incompatible.
- [ ] Same public item can produce different explained assessments for different personas/users.
- [ ] Private imports, feedback, and matches cannot leak across users.
- [ ] Ranking is reproducible for fixed inputs; score is not described as a hiring probability.

## 4. Outreach and documents

- [ ] Structured resume source and immutable document versions with downloadable export.
- [ ] Candidate-evidence selection for an opportunity.
- [ ] Relevant introduction, DM/email draft, and targeted resume preparation.
- [ ] Optional LLM adapter with useful template/manual fallback and server-side configuration.
- [ ] Review/edit workflow and supporting references for generated claims.
- [ ] Associate exact resume/document versions with applications.
- [ ] Follow-up workflow based on explicit activity timestamps.

Acceptance:

- [ ] Generated materials use only candidate-supported claims; missing evidence is surfaced, not fabricated.
- [ ] User can edit and export usable materials without an LLM key.
- [ ] Prior submitted versions remain unchanged after later editing.
- [ ] Document URLs/storage access enforce ownership.
- [ ] Generation/provider/PDF failures leave application tracking usable and show actionable errors.

## 5. Coach, analytics, and V1 readiness

- [ ] Deterministic daily priorities from due tasks, active applications, and qualified opportunities.
- [ ] Optional AI coach grounded in authorized profile/evidence/pipeline data.
- [ ] Source and funnel analytics with defined events, time ranges, and denominators.
- [ ] Explicit insufficient-data states rather than unsupported conclusions.
- [ ] Loading, empty, validation, and failure states across the main loop.
- [ ] Backups/restore approach, deployment assumptions, and operational runbook documented.
- [ ] Basic source/provider usage telemetry and configuration limits.

Acceptance:

- [ ] Coach answers cite or link to supporting app records and distinguish uncertainty.
- [ ] External post/JD instructions cannot override coaching instructions or access boundaries.
- [ ] Priorities work without LLM credentials and do not invent activity.
- [ ] Two-user checks cover records, joins, feed, documents, and coach context.
- [ ] End-to-end verification covers capture → qualification → contact/evidence → draft/export → explicit application/outreach → follow-up.
- [ ] Relevant automated checks pass; remaining limitations and any untested live integrations are documented.

## Deferred until justified

- Paid LinkedIn post providers and direct proxy infrastructure: evaluate against the manual baseline first.
- Automated message sending and job submission.
- Broad web-wide startup or social-interaction crawling.
- Human expert marketplace.
- Vector search or service decomposition without a demonstrated need.

## Current handoff

### Completed

- Product planning and predecessor review.
- Founder preferences captured: three role families, India remote + contracting + relocation, free-first discovery, AI coach first.
- `PRODUCT_PLAN.md`, `AGENTS.md`, and this checklist added to the new repository.
- Foundation and the first workspace profile slice implemented and verified on 2026-11-06.
- Dedicated project-owned PostgreSQL container/volume, as requested during implementation; default host port is **55432**. Existing Pixis FinOps containers do not conflict and were not stopped.

### Implementation state

- `apps/web`: Next.js/TypeScript authentication and redesigned responsive workspace with overview, resume upload/paste and review, profile preferences/dropdowns, search personas, proof-of-work CRUD, and actionable setup navigation. Every candidate field remains optional; existing free-text values survive dropdown upgrades.
- `services/api`: FastAPI, SQLAlchemy, PostgreSQL/Alembic; user/profile/session migration, Argon2id passwords, hashed opaque sessions, session rotation/expiry/revocation, write-origin checks, no-store responses, and owner-scoped profile reads/writes with optimistic version checks.
- `compose.yaml`: `resumatch-db-1`, `resumatch_postgres_data`, PostgreSQL 17, bound only to `127.0.0.1:55432`. Docker Desktop was started; container is running and healthy. Local ignored `.env` uses the example development configuration.
- `docs/0001-foundation.md`: auth and ownership boundary, migration tooling, chosen Procrastinate queue and local/S3 storage direction. Queue/storage implementations are intentionally scheduled with their first real milestone-2/4 use. Worker is a runnable connectivity check, not an ingestion runner.
- `uv.lock` and `apps/web/package-lock.json` record dependency versions. README contains setup/start/migration/interactive-account-seed/test commands.
- Real PostgreSQL tests cover authentication, password/token storage, expiry/logout/rotation, ownership injection, two-user reads/writes, profile constraints, lost-update conflicts, and cross-origin writes. A Chromium test uses real API/database processes and two browser contexts.
- Foundation, profile, evidence and persona slices are implemented, with resume-import review brought forward to improve onboarding. Milestone 1 is **not** complete: company/contact records, opportunity capture, applications, outreach and tasks remain. No ranking, generated-document export, live connector or coach implementation yet. No paid/live LLM provider integration was tested.

### Next concrete step

Continue section 1 with **company/contact records and manual role/hiring-post capture**, connecting saved personas and candidate evidence to the opportunity detail. Then implement durable application history, outreach and follow-up tasks so the overview advances into a real search pipeline. Read ADRs 0001/0002 before extending private joins/imports. Current migration head is `0003_resume_import`; update readiness when adding migrations. Separately, obtain the endpoint/model belonging to the user's stored LLM key before any live extraction-provider check.

### Open inputs

The user supplied resume text in the conversation and has saved personal profile details through the app. These remain private user-provided claims to review; do not add them as global defaults or committed fixtures. A key is now in ignored `.env`; its provider URL and supported model ID remain unspecified. User clarified Astra is the coding model, not the app extraction provider. Board watchlist and deployment target remain open. Continue independent implementation without inventing compensation/eligibility details.

### Checks and results — 2026-11-06

All commands ran from the root except npm commands, which ran in `apps/web`.

- `docker desktop start`, `docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'`: started the previously stopped daemon and confirmed no container conflicts. Host PostgreSQL on 5432 and Pixis FinOps DB on 54322 remain independent.
- `docker compose up -d --wait db`: downloaded PostgreSQL image, created dedicated network/volume/container, healthy.
- `docker compose exec -T db createdb -U resumatch resumatch_test`: created separate disposable test DB.
- `uv sync`, then `uv run alembic upgrade head && uv run alembic check`: installed locked dependencies, migrated development database, no schema drift.
- `uv sync --frozen && uv run alembic current && uv run alembic check && uv run python -m resumatch.seed --help`: locked setup passed, development DB at `0001_identity_profile (head)`, no drift, seed entrypoint available.
- `uv run ruff check . && uv run ruff format --check . && uv run pytest -q && uv run python -m resumatch_worker --check`: all lint/format checks passed; **13 tests passed** on real PostgreSQL with migrations from an empty public schema; worker connectivity passed. One upstream Starlette/httpx deprecation warning remains.
- System Node is 22.11, below a lint dependency's supported version. Used `npm exec --yes --package=node@22` to run Node **22.23.4** without changing the host Node install. README requires Node 22.13+.
- `npm exec --yes --package=node@22 -c 'npm ci && npm run typecheck && npm run lint && npm run build'`: clean lockfile install, TypeScript, ESLint, and production build passed.
- `npm exec --yes --package=node@22 -c 'node node_modules/@playwright/test/cli.js install chromium && npm run test:e2e'`: Chromium installed (one download timeout retried successfully); **1 browser test passed**, actual web/API processes with test database and two identities. Playwright stopped its app processes afterward.
- `docker compose exec -T db psql -U resumatch -d resumatch_test -c "SELECT count(*) AS saved_profiles FROM candidate_profiles WHERE details->>'display_name' = 'Private browser candidate';"` returned **1** both before and after `docker compose restart db && docker compose up -d --wait db`; saved profile survived a real database-container restart.
- `npm audit --omit=dev`: **0 production vulnerabilities**. Full `npm audit` reports **8 moderate dev-tool findings** through the TypeScript ESLint parser's transitive minimatch dependency. npm's proposed force fix downgrades Next's ESLint config to a different major; not applied. Revisit with a compatible upstream dependency update. ESLint 9 also reports an upstream support deprecation.
- `git diff --check`: passed. No commits or deployments made.

### Remaining limitations / configuration

- Public deployment needs HTTPS/secure cookies, registration policy, edge auth rate limiting, recovery/verification, session cleanup and restricted DB roles (see ADR). Current local auth is real server-validated authentication, without email verification/recovery.
- API ownership checks are the enforcement boundary; no database RLS yet. Continue enforcing owners on every new private read/write/join, including linked IDs.
- Test databases ending in `_test` are disposable: API tests **drop the public schema**. Run API and browser checks sequentially. Browser tests leave clearly labeled accounts only in the test DB.
- Development database contains no invented candidate data. Start API/web with README commands and create your real account, or use the interactive seed command. The DB container is running; the initial foundation handoff did not leave dev web/API servers running.
- Profile details and all other open inputs remain user-editable/unknown. No founder answers are required to continue the next slice.

### Follow-up fix: local registration origin mismatch — 2026-11-06

- User reported registration failing with “Request origin is not allowed.” Reproduced through the running app: an empty registration payload with `Origin: http://localhost:3000` reached validation (422), while `Origin: http://127.0.0.1:3000` was rejected (403).
- Added validated `WEB_ADDITIONAL_ORIGINS` (explicit JSON list), preserving exact scheme/host/port checks. Updated `.env.example` and local ignored `.env` to allow `http://127.0.0.1:3000` alongside the primary `http://localhost:3000`. Missing/untrusted origins still fail; errors now explain the configured URL and remedy. API reload picked up the fix.
- Tightened configured-origin validation to reject paths, queries, credentials and malformed ports. Added regression checks for alternate-origin authentication/profile writes, absent/untrusted/wrong-port origins, and invalid configuration.
- Browser checks now exercise the complete existing auth/profile flow through **both** `localhost` and `127.0.0.1`. The first run encountered Next's dev-server lock because the user already had the app running. Added a separate `.next-e2e` build directory so checks run alongside the user's dev server; no user app processes were stopped.
- `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`: passed, **21 tests**, same upstream deprecation warning.
- From `apps/web`, `npm exec --yes --package=node@22 -c 'npm run test:e2e && npm run typecheck && npm run lint'`: passed, **2 browser tests**, TypeScript and ESLint.
- Retried the live app probe for `http://127.0.0.1:3000`: now reaches request validation (422 for deliberately empty credentials), rather than failing origin checks. Real account creation verified with disposable test accounts in browser tests. User can refresh and retry registration at either supported local address.

### Guided workspace and resume import — 2026-11-06

User requested a full UX review, usable next steps after profile save, clearer dropdown fields, resume prefilling, a modern app, and explicitly authorized multiple agents. Work was divided across resume backend, workspace backend, frontend, and follow-up verification tasks, then integrated and checked together.

Implemented:

- Modern responsive desktop/mobile shell with real navigation, visible import → profile → personas → workspace sequence, actionable overview and counts from persisted records. Profile has **Save and continue to personas**. No fabricated pipeline metrics or inert feature navigation.
- Common dropdown choices plus custom/unknown values for availability, notice, timezone/overlap, relocation and currency. Existing saved custom text is preserved. Work authorization remains explicit rather than inferred.
- `workspace.py` and migration `0002_workspace`: private evidence CRUD with supporting quotes/URLs, multiple editable versioned personas and three role templates. Owner-scoped reads/writes/details, pagination, validated contracts and two-user checks.
- `resume_import.py`, `resume_extraction.py`, `storage.py`, migration `0003_resume_import`: 5 MB PDF/TXT upload or pasted text, 20-page/60,000-character limits, local parsing and optional server-only LLM adapter. Source-attributed proposals, immutable original source, private authenticated downloads, recent-import listing/reopening, review/edit/select before apply, and transactional profile-version/idempotency safeguards.
- Local parser handles typical introductory names/headlines, multiline summaries and evidence sections; approximate years stay in prose. Invalid/encrypted/scanned files offer paste-text guidance. AI proposals are schema/source checked; bad output and failures fall back visibly.
- Real LLM key removed from `.env.example` and preserved in ignored `.env` without printing it. `.env.example` has empty `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` and configurable `RESUME_STORAGE_PATH`. Missing endpoint/model means **no external request**, useful local extraction, and a configuration warning. No endpoint/model guessed or live success claimed.
- Tests forcibly disable live LLM credentials; provider behavior tested with synthetic mock transport. No actual resume/person contact information committed as fixtures, and no existing user profile replaced automatically.
- README and ADR 0002 document workflow, configuration, source/review boundaries, limits, and local upload backup needs. Typechecking now generates Next route types first so fresh checkouts do not depend on prior `.next` artifacts.

Verification:

- `uv sync && uv run alembic upgrade head && uv run alembic check`: dependencies installed and development DB migrated without schema drift or replacing existing profiles.
- Final `uv run ruff check . && uv run ruff format --check . && uv run pytest -q && uv run alembic current && uv run alembic check`: **82 tests passed**, lint/format passed, head `0003_resume_import`, no schema drift. Includes successful synthetic PDF upload/parsing, invalid files, proposal/apply conflicts and retries, owner-isolated files/import lists, persona/evidence CRUD, and mocked-provider claim/failure/config checks. Existing upstream Starlette/httpx deprecation warning remains.
- From `apps/web`, `npm exec --yes --package=node@22 -c 'npm run test:e2e && npm run typecheck && npm run lint && npm run build'`: **4 browser tests passed**, TypeScript/ESLint/production build passed. Tests cover both local origins, registration/logout/login, saved-field protection, upload/paste, reviewed editing, selected evidence, recent-import reopen after refresh, already-applied read-only state, dropdown/custom persistence, persona/evidence lifecycle, two browser identities and responsive no-overflow at 1440px/390px.
- Reviewed screenshots under ignored `apps/web/test-results/` for desktop/mobile overview, profile, import review and libraries. Fixed mobile grid/sidebar overflow during verification.
- `curl --fail -sS http://127.0.0.1:8000/api/health/ready`: healthy against the migrated development database. User's dev API/web processes and project database remain available.
- `git diff --check`: passed. `.env.example` key presence check is false; ignored `.env` key presence true; provider URL/model still absent. No commit or deployment.

Remaining scope/limitations:

- Resume extraction is working **locally**; real LLM integration still needs the actual provider endpoint/model. The key alone is insufficient. Astra was confirmed as coding-model preference only.
- Original PDF attachment was not available as a workspace file; supplied parsed content informed the workflow but was not silently imported into an account. Upload it or paste the supplied text in **Import resume** to review/apply to the authenticated account.
- Scanned PDFs need OCR outside this slice. Full document generation/export and immutable submitted application versions remain milestone 4 work; stored resume-import files do not satisfy that entire milestone.
- Private original-import deletion/retention, S3 adapter, public-deployment upload limits and full backup/restore runbook remain operations work. Back up both PostgreSQL and `.local/resumes` when retaining real uploads.
- Persona configuration versions increment; historical matching snapshots will be added with milestone 3. Opportunity discovery/pipeline/coach tasks remain unchecked above.
