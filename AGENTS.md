# Outreach sessions — agent handoff

Docs live outside this repo in ~/f/personel-docs/resumatch/ (github satvik-1945/personel-docs).
Read codebase-guide.md, product.md and the latest dev-log.md entries first. They replace the old
resume-first product.
The user explicitly requested resetting this repository and its two project databases.
Do not resurrect archived milestones or rebuild a broad job-search suite.
The reset is historical, not permission to reset again: real user contacts now exist and must
be preserved. Current hierarchy is workflow → dated run/session → captures. See codebase-guide.md.

Build one useful loop: start a session → browser-assisted capture → review → approved history.
First customer: Satvik's international startup/fintech job search. LinkedIn is an initial
channel label, not a verified inbox integration. Keep source URLs, unknowns and manual fallback.

- Draft, research, sent, follow-up and reply are different actions. Only reviewed records count.
- Connection requests and initial messages are distinct actions. Never infer them from profile text.
- Capture uses Contact URL + Raw capture text. Process with AI uses the run's versioned DSL and
  JSONata, fills empty fields only, and never auto-approves. Do not restore a separate source-text panel.
- Timer measures session time, not proven focused work. Pauses and restarts must be durable.
- Capture is explicit: no passive inbox monitoring, automatic sending, or guessed contact facts.
- LinkedIn is manual-only: no LinkedIn DOM/title/selection reads or page overlays. Never claim
  platform approval from a lack of HTML modification. See decisions/linkedin-policy.md.
- Everything is private. Public aliases, maps, groups and sharing come after the first real test.
- Keep the dedicated PostgreSQL container on 55432. Do not touch other project databases.
- Use Next.js/TypeScript, FastAPI, SQLAlchemy and Alembic; keep the first slice small.
- Validate identity, ownership, extension pairing, URLs and transitions on the server.
- Keep secrets in ignored .env. Do not print them or place them in browser bundles.
- Test real PostgreSQL and browser capture; fixtures do not establish live provider access.
- No commits, deployment, purchases or agent delegation unless explicitly requested.
- Append to personel-docs/resumatch/dev-log.md with exact results and next experiment. Keep the
  codebase guide and README commands current. Do not commit/push the docs repo unless asked.
