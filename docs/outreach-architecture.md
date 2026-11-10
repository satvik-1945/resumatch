# Outreach session slice — implementation decisions

## Runtime and reset
Next.js/TypeScript web app, FastAPI synchronous domain API, SQLAlchemy and Alembic on PostgreSQL.
Existing language/package scaffolding and the dedicated Compose DB are retained; old product code,
migrations, accounts, profile/persona/evidence/import tables and local uploaded resumes were reset
at the user's explicit request. Only planning documents were archived. No dormant resume workflow.

Six domain tables: users, logins, outreach_sessions, session_events, captures, extension_pairings.
The DB also holds alembic_version. There is no separate people/company catalog yet; reviewed capture
fields hold optional names plus source provenance. Avoid premature entity merging/enrichment.

## Identity and boundaries
- Local email/password identity, Argon2id, opaque 256-bit session cookies with hashed tokens stored
  server-side. HttpOnly/SameSite=Lax, seven days, rotation on login, revocation on logout.
- Same-origin Next `/api` proxy; writes require an exact allowlisted web Origin.
- All session/capture reads and mutations enforce ownership, including joins and guessed IDs.
- Current local setup assumes trusted localhost API/database processes. Before public release:
  HTTPS/Secure cookies, account recovery, auth rate limiting, restricted DB roles and backups.
  No claim of production authentication readiness; no database RLS in this slice.

## Session state machine and time
active → paused → active; active/paused → review → completed. No new session until the previous
session completes. A partial unique index and user-row lock enforce one open session even under
concurrent starts. Transitions lock the session, reject incompatible state, and persist events in
the same transaction. Active time is accumulated when pausing/finishing; running_since is durable
across reloads/process restarts. Page closure does not silently pause a session. Clock is server UTC.
It measures session time, not physiological effort or proof of focused work.

## Capture and review
- Input fields/URLs/action types are validated server-side. No URL fetching or hidden enrichment.
- Capture only in an active owned session. Limit 200 captures per session. Request IDs are unique
  within a session, and a retry returns the original capture without changing it.
- Store immutable original context separately from reviewed details. Captures begin pending;
  approval/discard happens only in review state and only once. All pending captures must be resolved
  before completion. Sent/followed-up/replied approval requires a named person and confirmation.
- Original/source timestamps and review timestamps differ. No claim that a web visit sent a message.
- Weekly action counts use approval time in the current Monday-start UTC week. Session goals count
  completed sessions with approved records. This is not a unique-people or response-rate metric.
- Follow-up dates use UTC day boundaries. Clearing a reminder is not a follow-up send event.

## Browser capture
Chrome MV3 uses activeTab, scripting and storage. No installed content scripts, browsing listeners
or all-sites host permission. The user invokes the toolbar/shortcut, and only title/URL/selected
text are collected; names/company/action are editable and unknown by default.

Pairing is initiated by the authenticated web user for a Chrome extension ID. A random token is
shown once, stored hashed on the API, and expires in seven days. It grants current-session summary
and capture creation only. Browser requests send bearer token and X-Extension-ID. The ID must match
the pairing, and any supplied Origin must match chrome-extension://<id>. Real Chrome testing showed
privileged GETs can omit Origin, so missing Origin is supported with token+ID. This ID is an audience
check, not cryptographic proof of a client executable: possession of the bearer credential grants
the narrow capture capability. Revocation is server-enforced.

Host permissions cover loopback API ports 8000 and test 8001. Extension storage access is limited
to trusted extension contexts. The popup keeps a draft before transmitting; retries use the same
ID. Users can discard that local draft before a new capture. No passive network traffic monitoring.

## Verification boundary
Real PostgreSQL tests cover ownership, transitions, timer persistence, action honesty, review,
idempotency and token scopes/revocation. A persistent Chromium context loads the actual unpacked
extension and tests its pairing/capture workflow, DOM-selected source and API storage/review.
Its source is a controlled loopback page covered by API host permission. A real user's toolbar
grant on LinkedIn/news sites remains the next manual experiment. No fixture claims provider access.

## Discovery and MCP
daily.dev's official API/MCP documentation is verified; live account access is not. No user token
was supplied. First use daily.dev as a source to open and capture. Later add a read-only, quota-bounded
discovery adapter and an MCP capture interface over the same domain API. No speculative agent chain
or LLM required for the logging loop.
