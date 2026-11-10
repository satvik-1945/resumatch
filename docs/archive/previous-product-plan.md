# Resumatch — Product Plan

Status: superseded by the outreach-session reset. Historical reference only.

## 1. Mission

Build a personalized job-search workspace that helps a candidate discover hiring intent, find the right person, present relevant proof of work, and manage the relationship through to an offer.

The first customer is the founder, Satvik. First make his international startup search genuinely useful, then expand to other candidates with individually personalized feeds.

Success means qualified opportunities, relevant conversations, interviews, offers, and time saved. Scrape volume is an operational metric, not the product outcome.

Core loop:

```text
Discover → qualify → explain fit → identify contact
         → prepare proof → apply / reach out → follow up
         → learn from the outcome
```

## 2. Founder context and confirmed decisions

- The predecessor, Anna Resumatch, won third prize in the Anna hackathon.
- Satvik subsequently landed a job at Revzio and currently works there, in a Singapore-based startup context.
- Channels that helped: recruiter/talent networks such as Hirojet, ClanX, Turing, and EliteBrains; LinkedIn hiring-intent searches; direct outreach; demonstrable work.
- The founder observes that international startups can value proof of work and hire remotely or through contracts. Treat this as a search hypothesis to validate, rather than a universal hiring rule.
- Target roles: **applied AI engineer**, **full-stack / founding engineer**, **backend / platform engineer**.
- Include **remote work from India**, **international contracting**, and **relocation opportunities**.
- Discovery budget: **free-first**. Hosting and LLM costs are separate; do not assume paid provider approval.
- Coaching: **AI search coach first**, grounded in actual evidence and search activity.
- Build a standalone web application, ground up, with durable storage and a path to multi-user operation.

Still unknown: exact years of experience, seniority, verified stack, compensation floor, notice period, timezone overlap, relocation destinations, work authorization, and provider credentials. Model these as optional onboarding fields. Do not invent them or block foundational implementation on them.

## 3. Lessons from the predecessor

Reference repository: `/Users/satviktejas/f/anna-experiments` (may be unavailable on another machine).

Useful references: `README.md`, `executas/`, `bundle/`, and `scraper-experiments/SCRAPER_CATALOG.md`.

Implemented predecessor flow:

```text
One local profile → collect jobs → tailor LaTeX Skills section
                  → application packs / PDF → manual application tracking
```

It uses a vanilla JavaScript Anna dashboard and Python executas, local JSON files, and browser-local statuses. It collects JobSpy listings and public remote-board data. Optional LinkedIn support concerns **job listings**, not hiring posts.

Limitations to address:

- No durable relational application history or multi-user isolation.
- No multiple search personas or genuinely ranked personalized feed.
- Mostly literal skill overlap; no structured international hiring eligibility.
- Fetches replace current datasets; some pipeline associations depend on array indices.
- Resume work happens too early across many collected jobs.
- Scraper catalog entries are research candidates, not validated integrations.
- Generated skills must not introduce unsupported candidate claims.

Retain the workflow lessons, provenance, manual submission, and local refinement after collection. Build new foundations rather than copying the old storage or runtime architecture.

## 4. Product modules and features

### A. Candidate profile and proof-of-work library

Answer: “What can this person credibly demonstrate?”

- Structured experience, education, skills, availability, location, notice period, and compensation preferences.
- Resume upload/import; allow manual editing and correction of extracted content.
- Projects, repositories, demos, articles, and achievements with supporting links.
- Connect skills and claims to supporting experience or projects.
- Immutable resume/document versions; preserve the exact material used for an application.
- Anna's award and Revzio experience are candidate evidence to add and verify through onboarding; do not invent details or performance metrics.
- Distinguish candidate-supported skills, job-required skills, and approved resume claims.

### B. Search personas

A persona represents a specific search strategy, not a separate user identity.

Initial personas:

| Persona | Target |
| --- | --- |
| Applied AI engineer | Startups building AI-powered products |
| Full-stack / founding engineer | Small teams seeking broad product ownership |
| Backend / platform engineer | APIs, backend systems, infrastructure, platform work |

Each stores role aliases, seniority, required/preferred technologies, industries, company stages, compensation preferences, geography, employment arrangements, timezone availability, exclusions, and saved queries.

Evaluate remote employment, contracting, and relocation independently. Support multiple personas per user and configuration versions for reproducible matching.

### C. Opportunity discovery

| Channel | Initial approach |
| --- | --- |
| Recruiter/talent networks | Directory seeded with Hirojet, ClanX, Turing, EliteBrains; track links, profiles, contacts, roles, and check-ins |
| Company careers | Curated startup watchlist with careers URLs |
| Public ATS listings | Greenhouse and Lever connectors |
| LinkedIn hiring posts | Saved searches and manual URL/text capture |
| YC and funded startups | Discover companies, then verify current hiring |
| Remote boards | Add selectively based on measured useful results and available access |
| Personal discoveries | Paste URL and description from any source |

Recruiter names are research targets, not assumed API integrations. Greenhouse and Lever collection is per known company board/site, not a global job-search API. Begin with user-selected companies and board identifiers.

Funding or YC membership indicates a research lead, not proof of current hiring.

### D. Company and contact intelligence

Answer: “Why this company, why now, and who should I contact?”

- Company identity, domain, product, industry, headquarters, stage, and careers URL.
- Funding claims with source and date when available.
- Contacts and company affiliations: founders, engineering leaders, hiring managers, recruiters.
- Hiring posts linked to companies, people, and roles.
- Remote-hiring evidence, freshness, and unresolved questions.
- User-owned company watchlists.

Suggested contact priority:

1. Person explicitly hiring for the role.
2. Relevant hiring manager or engineering leader.
3. Founder at a small startup.
4. Recruiter handling the role.
5. Other relevant people discovered through public activity.

The founder's observation that founders engage with prominent company/YC posts is a discovery technique. A like or comment alone does not establish hiring intent. Verify company, role, and context before recommending outreach.

### E. Personalized feed

Support three card types:

- **Role:** an identifiable opening.
- **Hiring signal:** a post or statement indicating demand, potentially without a formal listing.
- **Company lead:** a promising company requiring investigation.

Every card should explain persona fit, eligibility and unknowns, hiring evidence, freshness, relevant candidate evidence, relevant contacts, and next action.

Eligibility precedes ranking:

```text
eligible | ineligible | unknown
```

Evaluate hiring country, employment arrangement, mandatory timezone overlap, work authorization, and relocation/sponsorship where relevant. Keep assessments specific to an arrangement. A single unknown field should not silently become eligible or automatically discard an otherwise useful lead.

“Remote” alone is not evidence that a company hires from India. Known incompatible hard constraints are excluded from the default qualified feed, while remaining accessible with an explanation. Unknowns are visibly labeled and can appear in a research lane.

Initial ranking factors:

- Role and seniority alignment.
- Demonstrated relevant experience.
- Company preferences.
- Strength of hiring intent.
- Freshness and verified open status.
- Contact relevance.
- Explicit user feedback.

Start with explainable deterministic rules and structured extraction. Store component scores, reasons, evidence references, and scorer/persona versions. Do not present a score as a hiring probability. Tune weights using reviewed results and outcomes.

### F. Application and outreach workspace

- Log existing applications and manually add opportunities.
- Save and qualify opportunities before applying.
- Prepare targeted resumes, introductions, project links, and outreach drafts.
- Track conversations, referrals, interviews, offers, and follow-ups.
- Preserve exact submitted documents and event history.
- Keep outreach status separate from application status: a DM is not automatically an application.
- Open the real application page for submission; record submission explicitly.

Suggested application stages: `draft`, `applied`, `screening`, `interviewing`, `offer`, `accepted`, `rejected`, `withdrawn`, `closed`.

Suggested outreach message states: `draft`, `sent`, `replied`. Manual tracking must be clearly labeled; drafting or opening a link must not imply sending.

### G. AI search coach

A coach grounded in profile, evidence, feed, and pipeline should answer:

- What are my best actions today?
- Which opportunities need investigation?
- Who needs a follow-up?
- Which proof of work should I lead with?
- Which channels produce replies and interviews?
- How should I prepare for this interview?

Reference the records behind advice. Treat external source text as data, not instructions. Provide useful deterministic daily priorities when LLM credentials are absent. Keep provider/model configuration outside domain logic.

## 5. Data model

Use PostgreSQL, stable IDs, foreign keys, UTC timestamps, indexes, and migrations. This is a target logical model; implement tables as their milestone requires them rather than building unused infrastructure first.

| Area | Tables | Core contents |
| --- | --- | --- |
| Identity | `users` | Identity and account settings |
| Candidate | `candidate_profiles` | Experience, location, availability, preferences |
| Evidence | `candidate_evidence` | Claims, projects, achievements, supporting links |
| Personas | `search_personas` | Roles, constraints, preferences, configuration version |
| Queries | `saved_searches` | Persona, source, exact query, search URL, schedule |
| Companies | `companies` | Canonical identity, domain, careers URL, attributes |
| People | `contacts`, `contact_affiliations` | Identity and company/role relationships |
| Sources | `sources`, `source_connections` | Connector definitions, board/site configuration, secret references |
| Collection | `ingestion_runs`, `source_items` | Run status, native IDs, URLs, payload references, hashes, timestamps |
| Opportunities | `opportunities` | Canonical role, hiring signal, or company lead |
| Job details | `job_details` | Requirements, salary/currency/interval, locations, employment terms |
| Posts | `hiring_posts` | Post text, author, dates, extracted intent |
| Provenance | `opportunity_sources`, `opportunity_contacts` | Supporting source records and relevant contacts |
| Eligibility | `eligibility_assessments` | Persona/opportunity/arrangement result, reasons, evidence, confidence, version |
| Feed | `match_results`, `user_opportunity_states` | Component scores, explanations, saved/seen/dismissed state, feedback |
| Pipeline | `applications`, `application_events` | Stage, timestamps, notes, historical events |
| Outreach | `outreach_threads`, `outreach_messages` | Opportunity/contact, channel, drafts, send/reply tracking |
| Documents | `documents`, `application_documents` | Immutable versions, storage keys, hashes, associations |
| Actions | `tasks` | Follow-ups, deadlines, interview preparation, completion |
| Watchlists | `company_watchlists` | User-owned company selection |
| Coaching | `coach_sessions`, `coach_messages` | Conversations and supporting record references |

Relationships:

```text
User → Profile → Evidence
User → Personas → Matches ← Opportunities
Company → Opportunities
Contacts ↔ Companies
Source items → Opportunities
User → Applications → Events + Documents
User → Outreach → Contact
```

Data requirements:

- Separate shared public discovery records from private user activity.
- User-owned records carry `user_id`; enforce access in API queries and database row policies where applicable.
- Manual imports, notes, contacts, and extracted private data remain private by default. Explicitly distinguish shared and private records in schema and access rules, including joined results.
- Public discovery records can be collected once and matched to multiple users. Private artifacts must not leak through deduplication, search, coaching context, or document URLs.
- Deduplicate on source-native IDs first; use canonical URLs and company/role attributes for cross-source candidates. Preserve all provenance and avoid merging distinct openings solely by title.
- Record `published_at`, `first_seen_at`, `last_seen_at`, and `verified_at` separately. Missing publication time stays unknown; a fetch time is not a publication date.
- Separate extracted source facts from model-inferred assessments and user corrections.
- Store explicit eligibility evidence, allowed-country/timezone constraints, arrangement, and uncertainty; JSONB is acceptable for evolving structured constraints if validated.
- Keep closed/stale opportunities and application history. Do not delete historical applications when a listing disappears.
- Persist status change and event creation transactionally.
- Store resume and source files in object storage; store metadata and object keys in PostgreSQL.
- Source credentials are server-side secrets or secret references, never public database fields or frontend configuration.

## 6. LinkedIn posts and proxy strategy

### Free-first launch

Build the post workflow immediately. Buy proxy infrastructure only if a collection experiment establishes value and access feasibility.

A proxy transports requests. It does not supply discovery, parsing, reliable coverage, or permissions. JobSpy's listing support does not unlock LinkedIn post search.

Preserve the founder's successful search exactly:

```text
"hiring" AND ("client is looking for" OR "remote opportunity" OR "US startup") AND ("software engineer" OR "backend")
```

Original URL:

```text
https://www.linkedin.com/search/results/all/?keywords=%22hiring%22%20AND%20%28%22client%20is%20looking%20for%22%20OR%20%22remote%20opportunity%22%20OR%20%22US%20startup%22%29%20AND%20%28%22software%20engineer%22%20OR%20%22backend%22%29&origin=GLOBAL_SEARCH_HEADER
```

This URL searches all results. Also save a Posts-filtered version selected and checked in LinkedIn's UI rather than assuming undocumented URL filters work.

Workflow:

1. Save the exact search and create role-specific variants.
2. Open the search in LinkedIn.
3. Capture a post URL and pasted text into Resumatch.
4. Extract role, company, author, date, location constraints, and contact instructions; permit corrections.
5. Link to a canonical opportunity or create a hiring signal.
6. Match to personas and suggest a next action.

Test shorter query variants involving “founding engineer,” “AI engineer,” “APAC,” and “contractor.” Do not replace the proven original query.

### Automation options

| Method | Planned use |
| --- | --- |
| Manual URL/text capture | Launch baseline; must work without credentials |
| Search-engine-indexed public posts | Supplementary, incomplete discovery; dependent on search access |
| Managed post provider | Later, bounded evaluation |
| Direct collection with proxies | Consider after proving value and maintenance needs |
| Official LinkedIn Posts API | Restricted access; not an unrestricted public keyword-search feed |

Anna's catalog lists Apify actors as research candidates. Do not treat their existence, coverage, prices, or claims as verified.

Before choosing a provider or proxy service, compare against manual collection:

- Relevant unique posts and duplicate rate.
- Actual age and timestamp accuracy.
- Author/company extraction quality.
- India-remote and contracting relevance.
- Cost per useful opportunity.
- Failure rate, access constraints, and maintenance burden.

Use an interchangeable connector interface. When later adding proxies, keep them server-side and source-specific, with health telemetry, bounded retries, cooldowns, and spending limits. No paid provider or account-session collection is required for V1.

## 7. Architecture

Recommended initial stack:

- **Next.js + TypeScript** for the web application.
- **FastAPI + Python** for the domain API, extraction, and source connectors.
- **PostgreSQL** for persistence and initial full-text search.
- **Python worker** for ingestion, enrichment, and document generation.
- **PostgreSQL-backed durable task queue** initially; choose a maintained library or justify a minimal implementation with safe claiming/retries.
- **S3-compatible object storage** for documents/artifacts; a local development adapter is acceptable.
- Interchangeable discovery and LLM adapters.

```text
Web app → API → PostgreSQL / object storage
                 ↑
Scheduler → durable tasks → workers → source providers
```

Build a modular monolith with separate worker execution. Collect shared public data once and rank per persona. Avoid premature service decomposition. Introduce vector search only when a demonstrated need justifies it.

Suggested repository layout (adapt to actual scaffolding):

```text
apps/web/
services/api/
services/worker/
packages/                 # only genuinely shared contracts/utilities
infra/
docs/
```

Operational foundations: migrations, idempotent ingestion, source-specific rate limits, bounded retries, pagination, timeouts, freshness checks, structured logs, source-run health, cost tracking, backups, and reproducible local setup. Isolate PDF/LLM/provider failures from basic application use. Local development and tests must not require paid services.

Authentication must establish a real server-validated user identity. Do not expose an unauthenticated user-ID selector as production authentication. Record the chosen auth approach and deployment assumptions in an architecture decision.

## 8. Delivery milestones

### Milestone 1 — Search workspace

Auth, profile, personas, candidate evidence, manual opportunity/post capture, company/contact records, application history, outreach tracking, tasks, and dashboard.

Complete when Satvik can manage his real search end to end, refresh/restart without losing data, and capture a post → identify a relevant contact → select evidence → track a next action.

### Milestone 2 — Automated discovery

Company watchlist, Greenhouse/Lever connectors, recruiter directory, saved LinkedIn searches, deduplication, scheduled collection, ingestion history.

Complete when selected company boards refresh reliably, repeated runs do not duplicate records, source failures are visible, and history survives updates/closures.

### Milestone 3 — Personalized feed

Arrangement-specific eligibility, ranking, explanations, research lane, feedback, freshness, and matching against multiple personas.

Complete when reviewed recommendations explain their evidence and uncertainty, exclude known hard mismatches from the default qualified feed, and respect private data boundaries.

### Milestone 4 — Outreach and documents

Evidence-grounded introductions and message drafts, targeted resume preparation/export, immutable versions, follow-up workflow.

Complete when pursued opportunities have usable materials, no unsupported candidate claims are silently introduced, and submitted/sent status is explicitly recorded.

### Milestone 5 — Coach and beta readiness

Daily priorities, grounded AI coach, funnel/source analytics, multi-user validation, operational documentation.

Complete when advice reflects actual activity, useful priorities work without LLM access, and isolation checks cover feed, records, files, and coach context.

V1 means completing this coherent personal-search loop across milestones 1–5, using deliberately narrow integrations. Milestone 1 is the first usable slice, not a claim that all V1 features are finished. See `V1_TASKS.md` for build order and acceptance criteria.

## 9. Measurement

Track qualified opportunities reviewed, outreach sent, replies, applications submitted, interviews, offers, overdue follow-ups, and time saved where measurable.

Report source conversion with explicit event definitions and denominators; insufficient data is not a meaningful trend. Record manual timestamps honestly. Use reviewed examples to improve feed relevance before expanding collection volume.

## 10. References

Checked during planning; documentation is not an end-to-end integration test:

- Greenhouse Job Board API: https://developers.greenhouse.io/job-board.html — public GET endpoints; collection is board-specific. Submission needs employer credentials and is outside the initial manual-apply flow.
- Lever Postings API: https://github.com/lever/postings-api — published listings per company site; not a global full-text search API. Application submission requires employer credentials.
- LinkedIn Posts API: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api — restricted member/organization read permissions, not unrestricted keyword discovery.
- Predecessor scraper research: `/Users/satviktejas/f/anna-experiments/scraper-experiments/SCRAPER_CATALOG.md`.
